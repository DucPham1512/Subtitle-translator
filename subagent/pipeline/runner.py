"""Stage orchestration and resume logic (NFR-R1), and the episode-level API: run, batch, finish review, render."""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from subagent.infra.joblock import job_lock
from subagent.kernel.errors import SubagentError
from subagent.kernel.models import (
    EditRecord,
    Episode,
    LineTranslation,
    NewVoice,
    ReviewedLine,
    StageState,
)
from subagent.kernel.progress import NULL_PROGRESS, Progress
from subagent.kernel.util import hash_path, now_iso, read_jsonl, sha256_json
from subagent.llm.client import LLMClient, missing_prices
from subagent.memory.manager import MemoryManager
from subagent.memory.store import MemoryStore
from subagent.output.delivery import OnExists, cleanup, deliver, output_folder, resolve_conflict, target_path
from subagent.pipeline.report import counts_text, episode_status, write_report
from subagent.pipeline.stages import RERUN_FROM, STAGE_BY_NAME, STAGES, StageDef, review_outputs
from subagent.settings.config import Config, Paths
from subagent.workspace.context import EpisodeContext
from subagent.workspace.episodes import Registry
from subagent.workspace.state import load_state, save_state

log = logging.getLogger(__name__)


@dataclass
class BatchItem:
    episode_id: str
    status: str                  # done | awaiting_review | skipped | failed | not_run
    cost: float = 0.0
    reason: str = ""
    error_code: str = ""

# -- runner ----------------------------------------------------------------------------------------

class Runner:
    def __init__(self, ctx: EpisodeContext, mode: str):
        self.ctx = ctx
        self.mode = mode
        self.state = load_state(ctx.work, ctx.episode.id)
        self.state.mode = mode  # type: ignore[assignment]
        save_state(ctx.work, self.state)

    def outputs(self, stage: StageDef) -> list[str]:
        return review_outputs(self.mode) if stage.name == "review" else stage.outputs

    def input_hash(self, stage: StageDef) -> str:
        cfg = self.ctx.config
        parts: dict = {
            "upstream": {u: self.state.stages[u].output_hash if u in self.state.stages else None for u in stage.upstream},
            "config": {s: cfg.section(s) for s in stage.config},
            "prompts": {p: prompt_hash(self.ctx.paths, p, cfg) for p in stage.prompts},
            "models": {r: cfg.llm.providers[r].model for r in stage.llm_roles if r in cfg.llm.providers},
        }
        if stage.name == "review":
            parts["mode"] = self.mode
        extra = stage.extra(self.ctx) if stage.extra else None
        if extra is not None:          # nothing extra: earlier hashes stay valid
            parts["extra"] = extra
        return sha256_json(parts)

    def output_hash(self, stage: StageDef) -> str:
        return sha256_json({o: hash_path(self.ctx.artifact(o)) for o in self.outputs(stage)
                            if self.ctx.artifact(o).exists()})

    def outputs_exist(self, stage: StageDef) -> bool:
        return all(self.ctx.artifact(o).exists() for o in self.outputs(stage))

    def is_off(self, stage: StageDef) -> bool:
        return stage.identification and not self.ctx.config.show.character_identification

    def mark_off(self, stage: StageDef) -> None:
        """A stage that does not run in this mode: recorded so downstream hashes change with the mode."""
        self.state.stages[stage.name] = StageState(status="off", input_hash="off", output_hash="off",
                                                   finished_at=now_iso())
        save_state(self.ctx.work, self.state)
        self.ctx.progress.emit(stage.name, "skipped", message="character identification is off")

    def is_current(self, stage: StageDef) -> bool:
        st = self.state.stages.get(stage.name)
        if st is None or st.input_hash != self.input_hash(stage):
            return False
        return st.status == "purged" or (st.status == "done" and self.outputs_exist(stage))

    def ensure_available(self, stage: StageDef) -> None:
        """A purged upstream stage whose outputs are needed again is regenerated first (5.23)."""
        for name in stage.upstream:
            up = STAGE_BY_NAME[name]
            st = self.state.stages.get(name)
            if self.is_off(up):
                continue
            if st is None or not self.outputs_exist(up):
                self.ensure_available(up)
                self.execute(up)

    def execute(self, stage: StageDef) -> None:
        ctx = self.ctx
        ctx.progress.emit(stage.name, "start")
        log.info("stage %s: start", stage.name)
        st = StageState(status="running", started_at=now_iso())
        self.state.stages[stage.name] = st
        save_state(ctx.work, self.state)
        t0 = time.monotonic()
        try:
            counts = stage.run(ctx) or {}
        except BaseException as exc:
            st.status = "failed"
            st.error = str(exc)
            st.duration_s = round(time.monotonic() - t0, 2)
            save_state(ctx.work, self.state)
            raise
        st.status = "done"
        st.input_hash = self.input_hash(stage)
        st.output_hash = self.output_hash(stage)
        st.finished_at = now_iso()
        st.duration_s = round(time.monotonic() - t0, 2)
        st.counts = {k: int(v) for k, v in counts.items()}
        if stage.name in self.state.purged:
            self.state.purged.remove(stage.name)
        save_state(ctx.work, self.state)
        log.info("stage %s: done in %.1fs %s", stage.name, st.duration_s, st.counts)
        ctx.progress.emit(stage.name, "done", message=counts_text(st.counts), duration_s=st.duration_s)

    def run_all(self, *, from_stage: str | None, force_stage: str | None) -> None:
        names = [s.name for s in STAGES]
        for name in (from_stage, force_stage):
            if name and name not in names:
                raise SubagentError(f"Unknown stage '{name}'. Stages: {', '.join(names)}", code="unknown_stage")
        from_index = names.index(from_stage) if from_stage else None
        for i, stage in enumerate(STAGES):
            if self.is_off(stage):
                self.mark_off(stage)
                continue
            forced = stage.name == force_stage or (from_index is not None and i >= from_index)
            if not forced and self.is_current(stage):
                self.ctx.progress.emit(stage.name, "skipped")
                continue
            self.ensure_available(stage)
            self.execute(stage)


# `run --rerun` forces every stage from the first one that reads memory (the glossary); the stages before it
# depend only on the video and config, so their resume check already reruns them when anything changed

def prompt_hash(paths: Paths, name: str, config: Config | None = None) -> str | None:
    """The general prompt, the series' notes for it, and for the translator the translation style file (all
    change what the model reads)."""
    p = paths.prompts / f"{name}.md"
    if not p.is_file():
        return None
    parts = [hash_path(p)]
    notes = paths.series_prompts / f"{name}.md"
    if paths.series and notes.is_file():
        parts.append(hash_path(notes))
    if name == "translator_system" and config is not None:
        style = paths.prompts / "registers" / f"{config.show.genre_register}.md"
        if style.is_file():
            parts.append(hash_path(style))
    return "+".join(parts)




# -- episode-level API -----------------------------------------------------------------------------

class Pipeline:
    def __init__(self, config: Config, paths: Paths, *, progress: Progress = NULL_PROGRESS, use_cache: bool = True,
                 llm: LLMClient | None = None, after_finish: list[Callable[[EpisodeContext], None]] | None = None):
        self.config = config
        self.paths = paths
        self.progress = progress
        self.use_cache = use_cache
        self.llm = llm
        self.after_finish = after_finish or []   # called with each finished episode (e.g. the baseline copy)
        self.registry = Registry(paths)

    def context(self, episode: Episode) -> EpisodeContext:
        ctx = EpisodeContext(self.config, self.paths, episode, registry=self.registry, progress=self.progress,
                             use_cache=self.use_cache, llm_override=self.llm)
        ctx.work.mkdir(parents=True, exist_ok=True)
        return ctx

    # -- run ----------------------------------------------------------------------------------------

    def run(self, ep_ref: str, *, mode: str | None = None, from_stage: str | None = None,
            force_stage: str | None = None, on_exists: OnExists = "fail", rerun: bool = False) -> str:
        """Process an episode. Stages whose inputs did not change are skipped (resume), unless `rerun`: then
        every stage from RERUN_FROM runs again with today's memory, and a human-mode review starts over."""
        episode = self.registry.resolve(ep_ref)
        mode = mode or self.config.review.mode
        if rerun and from_stage is None:
            from_stage = RERUN_FROM
        if mode == "auto":
            output_folder(self.config)   # auto mode ends in a render: fail before spending anything
        ctx = self.context(episode)
        self._warn_missing_prices()
        earlier = self.registry.earlier_not_done(episode)
        if earlier:
            msg = (f"Earlier episodes are not done yet ({', '.join(e.id for e in earlier)}); memory builds up "
                   "episode by episode")
            log.warning(msg)
            self.progress.emit("pipeline", "info", message=msg, error_code="order_warning")
        with job_lock(self.paths, episode.id), _episode_log(ctx.work):
            self.registry.set_status(episode.id, "running")
            try:
                Runner(ctx, mode).run_all(from_stage=from_stage, force_stage=force_stage)
                if mode == "auto":
                    self._finish(ctx, on_exists)
                    return "done"
                self.registry.set_status(episode.id, "awaiting_review")
                write_report(ctx)
                self.progress.emit("pipeline", "awaiting_review", message="Review the script in the app, then finish review")
                return "awaiting_review"
            except BaseException as exc:
                self._failed(ctx, exc)
                raise

    def run_batch(self, ep_refs: list[str], *, mode: str | None = None, on_exists: OnExists = "fail",
                  keep_going: bool | None = None, max_total_cost: float | None = None,
                  rerun: bool = False) -> list[BatchItem]:
        """Several episodes in episode-number order, one after another in this process (models load once).

        Episodes already done or waiting for review are skipped, unless `rerun` (each episode runs again, see
        `run`). On a failure, auto mode stops (later episodes
        build on the memory of earlier ones) and human mode carries on, unless `keep_going` says otherwise.
        `max_total_cost` stops before starting another episode once the batch has spent that much.
        """
        mode = mode or self.config.review.mode
        keep_going = (mode == "human") if keep_going is None else keep_going
        episodes = sorted({e.id: e for e in (self.registry.resolve(r) for r in ep_refs)}.values(),
                          key=lambda e: e.number)
        items: list[BatchItem] = []
        spent = 0.0
        prices = self.config.llm.prices
        for i, episode in enumerate(episodes, 1):
            label = f"{episode.id} ({i}/{len(episodes)})"
            if episode.status in ("done", "awaiting_review") and not rerun:
                items.append(BatchItem(episode.id, "skipped", reason=f"already {episode.status}"))
                self.progress.emit("batch", "info", done=i, total=len(episodes), message=f"{label}: skipped, already "
                                   f"{episode.status}")
                continue
            if max_total_cost is not None and spent >= max_total_cost:
                items += [BatchItem(e.id, "not_run", reason="batch cost limit reached") for e in episodes[i - 1:]]
                self.progress.emit("batch", "info", message=f"cost limit ${max_total_cost:.2f} reached: "
                                   f"{len(episodes) - i + 1} episodes not run", error_code="budget_exceeded")
                break
            self.progress.emit("batch", "progress", done=i - 1, total=len(episodes), message=label)
            before = episode_status(self.paths, episode, prices)["cost"]
            try:
                status = self.run(episode.id, mode=mode, on_exists=on_exists, rerun=rerun)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001 - reported per episode; the batch decides whether to go on
                cost = episode_status(self.paths, self.registry.get(episode.id), prices)["cost"] - before
                spent += cost
                items.append(BatchItem(episode.id, "failed", cost, str(exc), getattr(exc, "code", "error")))
                self.progress.emit("batch", "info", message=f"{label}: failed: {exc}",
                                   error_code=getattr(exc, "code", "error"))
                if not keep_going:
                    items += [BatchItem(e.id, "not_run", reason=f"stopped after {episode.id} failed")
                              for e in episodes[i:]]
                    break
                continue
            cost = episode_status(self.paths, self.registry.get(episode.id), prices)["cost"] - before
            spent += cost
            items.append(BatchItem(episode.id, status, cost))
        counts: dict[str, int] = {}
        for it in items:
            counts[it.status] = counts.get(it.status, 0) + 1
        self.progress.emit("batch", "done", done=len(episodes), total=len(episodes),
                           message=", ".join(f"{n} {s}" for s, n in counts.items()) + f"; ${spent:.4f}")
        return items

    def finish_review(self, ep_ref: str, *, on_exists: OnExists = "fail") -> str:
        from subagent.review.review import finish_review

        episode = self.registry.resolve(ep_ref)
        ctx = self.context(episode)
        self._warn_missing_prices()
        with job_lock(self.paths, episode.id), _episode_log(ctx.work):
            self.registry.set_status(episode.id, "running")
            try:
                from subagent.memory.characters import episode_character_ids

                store = MemoryStore(self.paths.memory_db)
                waiting = {c.id for c in store.returning_candidates(episode.number, self.config.memory.probation_window)}
                known = episode_character_ids(ctx.work, store.character_ids(), self.config.voice.new_voice_prefix,
                                              waiting)
                self.progress.emit("review", "start", message="validating review")
                finish_review(ctx.work, known, self.config.review.predelete_fragments, self.config.review.noise_max_han)
                self.progress.emit("review", "done")
                self._finish(ctx, on_exists)
                return "done"
            except BaseException as exc:
                self._failed(ctx, exc, fallback="awaiting_review")
                raise

    def render(self, ep_ref: str, *, on_exists: OnExists = "fail") -> Path:
        episode = self.registry.resolve(ep_ref)
        ctx = self.context(episode)
        with job_lock(self.paths, episode.id), _episode_log(ctx.work):
            previous = episode.status
            self.registry.set_status(episode.id, "running")
            try:
                final = self._render_and_deliver(ctx, on_exists)
                self.registry.set_status(episode.id, "done" if previous in ("done", "running") else previous)
                write_report(ctx)
                return final
            except BaseException as exc:
                self._failed(ctx, exc, fallback=previous)
                raise

    def clean(self, ep_ref: str) -> list[str]:
        episode = self.registry.resolve(ep_ref)
        ctx = self.context(episode)
        with job_lock(self.paths, episode.id):
            return cleanup(ctx.work, episode.id)

    def calibrate(self, ep_ref: str) -> list[Path]:
        from subagent.ocr.ingest import calibrate

        return calibrate(self.context(self.registry.resolve(ep_ref)))

    def calibrate_style(self, ep_ref: str):
        """Learn the series' subtitle style from one episode (5.4a); saved for every later episode."""
        from subagent.infra.media import imwrite_png, iter_gray_frames, probe
        from subagent.ocr.subtitle_style import calibrate, save_style, style_preview

        ctx = self.context(self.registry.resolve(ep_ref))
        source = ctx.require_source()
        info = probe(source)
        v = self.config.video
        fps = min(v.calibrate_fps, v.calibrate_max_bands / max(1.0, info.duration_ms / 1000))
        crop = v.subtitle_band.pixels(info.width, info.height)
        bands = list(iter_gray_frames(source, fps=fps, crop=crop))[: v.calibrate_max_bands]
        self.progress.emit("calibrate", "progress", message=f"learning the subtitle style from {len(bands)} bands")
        style = calibrate(bands, stable_range=v.stable_range, source=ctx.episode.id)
        path = save_style(self.paths.bootstrap, style)
        out = ctx.artifact("calibration") / "style.png"
        center_x = info.width / 2 - crop[0]               # the frame's centre column in the band
        imwrite_png(out, style_preview(bands[:: max(1, len(bands) // 12)][:12], style, self.config.ocr, center_x))
        return style, path, out

    # -- internals ----------------------------------------------------------------------------------

    def _warn_missing_prices(self) -> None:
        missing = missing_prices(self.config)
        if missing:
            msg = (f"No price configured for {', '.join(missing)}: those calls are tracked as unknown cost and the "
                   f"${self.config.budget.max_cost_per_episode:.2f} budget cannot be enforced for them")
            log.warning(msg)
            self.progress.emit("pipeline", "info", message=msg, error_code="price_missing")

    def _failed(self, ctx: EpisodeContext, exc: BaseException, fallback: str = "failed") -> None:
        code = getattr(exc, "code", "error")
        if code == "source_missing":
            status = "missing"
        elif isinstance(exc, KeyboardInterrupt):
            status = fallback if fallback != "failed" else "new"
        else:
            status = "failed" if fallback == "failed" else fallback
        with contextlib.suppress(SubagentError):
            self.registry.set_status(ctx.episode.id, status)  # type: ignore[arg-type]
        log.error("episode %s failed: %s", ctx.episode.id, exc)

    def _finish(self, ctx: EpisodeContext, on_exists: OnExists) -> None:
        """Memory update → render → deliver → report → cleanup."""
        self._check_output(ctx, on_exists)   # before any work, so no render is wasted
        self._memory_update(ctx)
        self._learn_voices()
        self._learn_sprites(ctx)
        self._render_and_deliver(ctx, on_exists)
        self.registry.set_status(ctx.episode.id, "done")
        write_report(ctx)
        for hook in self.after_finish:
            hook(ctx)
        if self.config.cleanup.auto:
            cleanup(ctx.work, ctx.episode.id)
            self.progress.emit("cleanup", "done")
        self.progress.emit("pipeline", "finished", message=f"{ctx.episode.id} done")

    def _check_output(self, ctx: EpisodeContext, on_exists: OnExists) -> Path:
        output_folder(self.config)
        return resolve_conflict(target_path(self.config, ctx.source), on_exists)

    def _memory_update(self, ctx: EpisodeContext) -> None:
        state = load_state(ctx.work, ctx.episode.id)
        key = sha256_json({"approved": hash_path(ctx.artifact("approved.jsonl")),
                           "edits": hash_path(ctx.artifact("edits.jsonl")) if ctx.artifact("edits.jsonl").exists() else None})
        prev = state.stages.get("memory")
        if prev and prev.status == "done" and prev.input_hash == key:
            self.progress.emit("memory", "skipped")
            return
        self.progress.emit("memory", "start")
        t0 = time.monotonic()
        approved = read_jsonl(ctx.artifact("approved.jsonl"), ReviewedLine)
        translations = read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)
        edits = read_jsonl(ctx.artifact("edits.jsonl"), EditRecord)
        from subagent.memory.characters import load_new_voices, review_voice_ids

        voices = load_new_voices(ctx.work)
        known = MemoryStore(self.paths.memory_db).character_ids() | {v.id for v in voices}
        for cid in sorted(review_voice_ids(approved, self.config.voice.new_voice_prefix) - known):
            # an NPC the reviewer created in review: treated like a new voice of this episode (probation)
            used = [x.event_id for x in approved if cid in (x.speaker, x.listener)]
            voices.append(NewVoice(id=cid, event_ids=used, cohesion=0.0))
        result = MemoryManager(self.paths, self.config).episode_update(
            ctx.episode.id, approved, translations, edits, ctx.llm, self._line_decisions(ctx, approved),
            voices, mode=state.mode or "human")
        state = load_state(ctx.work, ctx.episode.id)
        state.stages["memory"] = StageState(
            status="done", input_hash=key, finished_at=now_iso(), duration_s=round(time.monotonic() - t0, 2),
            counts={"applied": len(result.applied), "rejected": len(result.rejected), "conflicts": len(result.conflicts),
                    **{f"characters_{status}": n for status, n in result.lifecycle.items()},
                    **{f"probation_{kind}": n for kind, n in result.probation.items() if n},
                    **({"updates_held": len(result.held)} if result.held else {})},
        )
        save_state(ctx.work, state)
        self.progress.emit("memory", "done", message=counts_text(state.stages["memory"].counts))

    def _line_decisions(self, ctx: EpisodeContext, approved: list[ReviewedLine]) -> tuple[list[str], list[str]]:
        """What the reviewer removed and kept, for the script reviewer's memory. Lossless repeat merges are not
        the reviewer's decision; short lines kept and pre-deleted lines restored count as kept."""
        from subagent.review.review import original_draft
        from subagent.translation.script_review import han_count

        rc = self.config.review
        original = {x.event_id: x for x in original_draft(ctx.work, rc.predelete_fragments, rc.noise_max_han)}
        removed, kept = [], []
        for x in approved:
            o = original.get(x.event_id)
            if x.deleted:
                if not (o is not None and o.deleted and "script_repeat" in o.flags):
                    removed.append(x.zh)
            elif han_count(x.zh) <= self.config.script_review.memory_max_han or (o is not None and o.deleted):
                kept.append(x.zh)
        return removed, kept

    def learn_sprites_backfill(self) -> list[tuple[str, dict[str, int]]]:
        """Finished episodes in episode order: run the cast stage where it never ran, then learn sprites."""
        out: list[tuple[str, dict[str, int]]] = []
        if not self.config.show.character_identification:
            return out
        for episode in sorted(self.registry.load(), key=lambda e: e.number):
            ctx = self.context(episode)
            if episode.status != "done" or not ctx.artifact("approved.jsonl").is_file():
                continue
            with job_lock(self.paths, episode.id), _episode_log(ctx.work):
                if not ctx.artifact("cast.jsonl").is_file():
                    mode = load_state(ctx.work, episode.id).mode or "human"
                    Runner(ctx, mode).execute(STAGE_BY_NAME["cast"])
                self._learn_sprites(ctx)
            out.append((episode.id, load_state(ctx.work, episode.id).stages.get("sprites", StageState()).counts))
        return out

    def _learn_sprites(self, ctx: EpisodeContext) -> None:
        """The episode's trusted speakers teach the sprite bank (5.8b). Never fails the episode."""
        if not (self.config.show.character_identification and self.config.cast.enabled and self.config.cast.learn)                 or not ctx.artifact("cast.jsonl").is_file():
            return
        from subagent.cast.learning import learn_sprites

        state = load_state(ctx.work, ctx.episode.id)
        key = sha256_json({"cast": hash_path(ctx.artifact("cast.jsonl")),
                           "approved": hash_path(ctx.artifact("approved.jsonl"))})
        prev = state.stages.get("sprites")
        if prev and prev.status == "done" and prev.input_hash == key:   # counts must not be learned twice
            self.progress.emit("sprites", "skipped")
            return
        self.progress.emit("sprites", "start")
        t0 = time.monotonic()
        try:
            result = learn_sprites(self.config, self.paths, ctx.episode.id)
        except Exception as exc:  # noqa: BLE001 - the episode is finished either way
            log.warning("sprite learning failed: %s", exc)
            self.progress.emit("sprites", "info", message=f"sprite bank not updated: {exc}")
            return
        state = load_state(ctx.work, ctx.episode.id)
        state.stages["sprites"] = StageState(
            status="done", input_hash=key, finished_at=now_iso(), duration_s=round(time.monotonic() - t0, 2),
            counts={"talking_lines": result.lines, "confirmed": result.confirmed, "corrected": result.corrected,
                    "named": len(result.named), "added": result.added, "removed": result.removed})
        save_state(ctx.work, state)
        self.progress.emit("sprites", "done", message=counts_text(state.stages["sprites"].counts))

    def _learn_voices(self) -> None:
        """Reviewed speakers teach the voice bank. Never fails the episode: a missing model is only reported."""
        if not (self.config.show.character_identification and self.config.voice.learn_from_reviews):
            return
        from subagent.kernel.errors import ModelUnavailableError
        from subagent.voice.learning import learn_voices

        self.progress.emit("voices", "start")
        try:
            result = learn_voices(self.config, self.paths)
        except ModelUnavailableError as exc:
            self.progress.emit("voices", "info", message=f"voice bank not updated: {exc}",
                               error_code="model_unavailable")
            return
        except Exception as exc:  # noqa: BLE001 - the episode is finished either way
            log.warning("voice learning failed: %s", exc)
            self.progress.emit("voices", "info", message=f"voice bank not updated: {exc}")
            return
        message = f"{len(result.voices)} voices from {result.lines_used} lines"
        if result.auto:
            message += (f"; {result.auto.offered} auto-mode lines "
                        f"{'used' if result.auto.accepted else 'not used'} ({result.auto.reason})")
        self.progress.emit("voices", "done", message=message)

    def _render_and_deliver(self, ctx: EpisodeContext, on_exists: OnExists) -> Path:
        from subagent.output.render import render

        self._check_output(ctx, on_exists)
        self.progress.emit("render", "start")
        t0 = time.monotonic()
        tmp = render(ctx)
        final = deliver(tmp, target_path(self.config, ctx.source), on_exists)
        self.registry.update(ctx.episode.id, output_path=str(final))
        state = load_state(ctx.work, ctx.episode.id)
        state.stages["render"] = StageState(status="done", finished_at=now_iso(),
                                            duration_s=round(time.monotonic() - t0, 2))
        save_state(ctx.work, state)
        self.progress.emit("render", "done", message=str(final), output_path=str(final))
        return final


class _episode_log:
    """Attach work/<episode>/run.log to the package logger for the duration of a job (NFR-O1)."""

    def __init__(self, work: Path):
        self.path = work / "run.log"
        self.handler: logging.Handler | None = None

    def __enter__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = logging.FileHandler(self.path, encoding="utf-8")
        self.handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger("subagent").addHandler(self.handler)

    def __exit__(self, *exc: object) -> None:
        if self.handler:
            logging.getLogger("subagent").removeHandler(self.handler)
            self.handler.close()
