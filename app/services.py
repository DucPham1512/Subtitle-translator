"""Thin adapter over the core: episode status, memory read/write, review draft I/O (6.1).

The app writes only: review_draft.jsonl, bootstrap inputs, config / .env, and memory through MemoryManager.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from subagent.infra.joblock import job_lock_path, running_jobs
from subagent.kernel.models import (
    CastLine,
    Episode,
    Evaluation,
    LineTranslation,
    PartialSuggestion,
    ReviewedLine,
    ScriptDecision,
    SubtitleEvent,
    VideoInfo,
)
from subagent.kernel.util import lock_holder, read_jsonl
from subagent.memory.manager import MemoryManager
from subagent.memory.store import MemoryStore
from subagent.pipeline import STAGES, episode_status
from subagent.settings.config import Config, Paths, load_config
from subagent.workspace.episodes import AddCandidate, Registry


@dataclass
class EpisodeRow:
    episode: Episode
    status: str
    stages_done: int
    stages_total: int
    flags: int
    cost: float
    stage_states: dict[str, str] = field(default_factory=dict)
    unpriced_models: list[str] = field(default_factory=list)
    cost_by_agent: dict[str, float] = field(default_factory=dict)


@dataclass
class ReviewData:
    episode: Episode
    lines: list[ReviewedLine]
    events: dict[str, SubtitleEvent]
    translations: dict[str, LineTranslation]
    evaluations: dict[str, list[Evaluation]]
    video: VideoInfo | None
    read_only: bool
    script_notes: dict[str, str] = field(default_factory=dict)
    cast: dict[str, CastLine] = field(default_factory=dict)
    partial: dict[str, PartialSuggestion] = field(default_factory=dict)


def script_note(d: ScriptDecision) -> str:
    """The script review's note for a line; an OCR fix adds the suggested Chinese and the model's context check."""
    if d.action == "fix" and d.zh_fix:
        parts = [d.note, f"→ {d.zh_fix}", f"({d.evidence})" if d.evidence else ""]
        return " ".join(p for p in parts if p)
    return d.note


class Services:
    def __init__(self, root: Path):
        self.root = root
        self.config: Config
        self.paths: Paths
        self.reload()
        self._engine = None
        self._engine_key: object = None

    def reload(self) -> None:
        self.config, self.paths = load_config(self.root)

    @property
    def registry(self) -> Registry:
        return Registry(self.paths)

    @property
    def store(self) -> MemoryStore:
        return MemoryStore(self.paths.memory_db)

    def manager(self) -> MemoryManager:
        return MemoryManager(self.paths, self.config)

    # -- episodes -----------------------------------------------------------------------------------

    def effective_status(self, ep: Episode) -> str:
        """A `running` episode whose job process is gone was interrupted (cancelled or crashed)."""
        if ep.status == "running" and lock_holder(job_lock_path(self.paths, ep.id)) is None:
            return "interrupted"
        return ep.status

    def episode_rows(self) -> list[EpisodeRow]:
        rows = []
        for ep in self.registry.load():
            st = episode_status(self.paths, ep, self.config.llm.prices)
            stages = st["stages"]
            done = sum(1 for s in stages.values() if s in ("done", "purged", "off"))
            rows.append(EpisodeRow(episode=ep, status=self.effective_status(ep), stages_done=done,
                                   stages_total=len(stages), flags=st["flag_total"], cost=st["cost"],
                                   stage_states=stages, unpriced_models=st["unpriced_models"],
                                   cost_by_agent=st["cost_by_agent"]))
        return rows

    def prepare_add(self, inputs: list[Path], recursive: bool) -> list[AddCandidate]:
        return self.registry.prepare_add(inputs, self.config, recursive=recursive)

    def earlier_not_done(self, ep_id: str) -> list[str]:
        reg = self.registry
        return [e.id for e in reg.earlier_not_done(reg.get(ep_id))]

    def output_target(self, ep_id: str) -> Path:
        from subagent.delivery import target_path

        return target_path(self.config, Path(self.registry.get(ep_id).source_path))

    def discarded_by_rerun(self, ep_id: str, stage: str) -> list[str]:
        """Existing results that `run --from stage` will replace (shown in the confirmation)."""
        names = [s.name for s in STAGES]
        work = self.paths.episode_dir(ep_id)
        out = []
        for s in STAGES[names.index(stage):]:
            out += s.outputs
        out += ["review_draft.jsonl", "approved.jsonl", "edits.jsonl", "output.ass"]
        return [name for name in dict.fromkeys(out) if (work / name).exists()]

    def jobs_running(self) -> list[str]:
        return running_jobs(self.paths, exclude_self=False)

    def report_path(self, ep_id: str) -> Path:
        return self.paths.episode_dir(ep_id) / "report.md"

    # -- review -------------------------------------------------------------------------------------

    def review_candidates(self) -> list[Episode]:
        out = []
        for ep in self.registry.load():
            work = self.paths.episode_dir(ep.id)
            if (work / "review_draft.jsonl").is_file() or (work / "approved.jsonl").is_file():
                out.append(ep)
        return out

    def load_review(self, ep_id: str, *, read_only: bool | None = None) -> ReviewData:
        from subagent.stages.review import load_draft

        ep = self.registry.get(ep_id)
        work = self.paths.episode_dir(ep_id)
        awaiting = ep.status == "awaiting_review" or (
            (work / "review_draft.jsonl").is_file() and not (work / "approved.jsonl").is_file())
        ro = (not awaiting) if read_only is None else read_only
        lines = load_draft(work) if (awaiting and not ro) or not (work / "approved.jsonl").is_file() else \
            read_jsonl(work / "approved.jsonl", ReviewedLine)
        evaluations: dict[str, list[Evaluation]] = {}
        for ev in read_jsonl(work / "evaluations.jsonl", Evaluation):
            evaluations.setdefault(ev.event_id, []).append(ev)
        video = None
        if (work / "video.json").is_file():
            video = VideoInfo.model_validate_json((work / "video.json").read_text(encoding="utf-8"))
        return ReviewData(
            episode=ep, lines=lines,
            events={e.id: e for e in read_jsonl(work / "events.jsonl", SubtitleEvent)},
            translations={t.event_id: t for t in read_jsonl(work / "translations.jsonl", LineTranslation)},
            evaluations=evaluations, video=video, read_only=ro,
            script_notes={d.event_id: script_note(d) for d in read_jsonl(work / "script_review.jsonl", ScriptDecision)},
            cast={c.event_id: c for c in read_jsonl(work / "cast.jsonl", CastLine)},
            partial=self.partial_suggestions(ep_id),
        )

    def output_exists(self, ep_id: str) -> bool:
        try:
            return self.output_target(ep_id).exists()
        except Exception:  # noqa: BLE001 - no output folder yet: the job reports it
            return False

    # -- audit (6.11) -------------------------------------------------------------------------------

    def audit_overview(self) -> list[dict]:
        from subagent import audit
        from subagent.workspace.state import load_state

        rows = []
        for ep in sorted(self.registry.load(), key=lambda e: e.number):
            if ep.status != "done":
                continue
            work = self.paths.episode_dir(ep.id)
            sample = audit.load_sample(work)
            ok = audit.auditable(self.config, self.paths, ep.id)
            e = audit.build_report(self.config, self.paths, [ep.id]).episodes if sample and ok else []
            rows.append({"episode": ep.id, "mode": load_state(work, ep.id).mode or "-",
                         "lines": len(audit.auditable_lines(work)), "sampled": len(sample),
                         "marked": e[0].marked if e else 0, "errors": e[0].any_error.errors if e else 0.0,
                         "checked": e[0].any_error.checked if e else 0, "auditable": ok,
                         "missing": audit.missing_answers(work) if ok else 0})
        return rows

    def draw_audit_samples(self) -> int:
        """Samples for finished episodes that have none yet (existing samples are kept: marks refer to them)."""
        from subagent import audit

        drawn = 0
        for ep in self.registry.load():
            if ep.status == "done" and not audit.load_sample(self.paths.episode_dir(ep.id)):
                drawn += bool(audit.draw_sample(self.config, self.paths, ep.id))
        return drawn

    def audit_data(self, ep_id: str):
        from subagent import audit

        work = self.paths.episode_dir(ep_id)
        return {s.event_id: s for s in audit.load_sample(work)}, audit.load_marks(work)

    def save_audit_marks(self, ep_id: str, marks: dict) -> None:
        from subagent import audit

        audit.save_marks(self.paths.episode_dir(ep_id), marks)

    def audit_report(self) -> tuple[str, Path]:
        from subagent import audit

        eps = [e.id for e in sorted(self.registry.load(), key=lambda e: e.number)
               if e.status == "done" and audit.load_sample(self.paths.episode_dir(e.id))]
        report, path = audit.write_report(self.config, self.paths, eps)
        return audit.render_report(report), path

    def benchmark_history(self) -> tuple[str, Path | None]:
        """Markdown: every benchmark run (newest first) and the latest run's report."""
        import json

        folder = self.paths.work / "_benchmark"
        runs = []
        if (folder / "history.jsonl").is_file():
            runs = [json.loads(x) for x in (folder / "history.jsonl").read_text(encoding="utf-8").splitlines() if x]
        if not runs:
            return "No benchmark run yet.", None
        lines = ["| run | name | speaker accuracy | audited output | cost |", "|---|---|---|---|---|"]
        pct = lambda v: "n/a" if v is None else f"{v * 100:.1f}%"   # noqa: E731
        for r in reversed(runs):
            lines.append(f"| {r['at'][:16].replace('T', ' ')} | {r['label'] or '—'} | {pct(r['speaker_accuracy'])} | "
                         f"{pct(r['speaker_accuracy_before'])} | ${r['cost']:.4f} |")
        latest = Path(runs[-1]["folder"]) / "report.md"
        report = latest.read_text(encoding="utf-8") if latest.is_file() else ""
        return "# Benchmark runs\n\n" + "\n".join(lines) + "\n\n" + report, latest

    def partial_suggestions(self, ep_id: str) -> dict[str, PartialSuggestion]:
        from subagent.partial_review import OUTPUT

        return {s.event_id: s for s in read_jsonl(self.paths.episode_dir(ep_id) / OUTPUT, PartialSuggestion)}

    def line_frame(self, ep_id: str, start_ms: int, end_ms: int, event: SubtitleEvent | None,
                   video: VideoInfo | None):
        """The frame the cast stage used for a line (BGR, full video size) and the subtitle band crop
        (x, y, w, h). Raises when the video is missing."""
        from subagent.cast.cast import frame_time_ms
        from subagent.infra.media import extract_frame, probe

        ep = self.registry.get(ep_id)
        source = Path(ep.source_path)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        info = video or probe(source)
        t_ms = frame_time_ms(event, self.config.cast.sample_fps) if event else (start_ms + end_ms) // 2
        frame = extract_frame(source, t_ms, size=(info.width, info.height))
        from subagent.cast.cast import load_frame

        analysed = load_frame(self.paths.episode_dir(ep_id), event.id) if event else None
        return frame, self.config.video.subtitle_band.pixels(info.width, info.height), analysed

    def character_card(self, ep_id: str, char_id: str, draft: list[ReviewedLine], media: bool = True):
        """Who an id is (6.4): name, description, first episode, and a voice clip and picture from its example
        line (cut once, cached). `draft`: the lines of the episode under review."""
        from subagent.cast.card import card_info, card_media

        card = card_info(self.paths, self.config, char_id, current=ep_id, draft=draft)
        return card_media(self.paths, self.config, card) if media else card

    def pin_character_card(self, ep_id: str, line: ReviewedLine, cast: CastLine | None):
        """"Use this line": the line's voice and the box shown as talking in On screen (none: no picture) become
        its speaker's card sample. The card only; memory learns nothing from it."""
        from subagent.cast.card import pin_card, shown_talking_box

        return pin_card(self.paths, self.config, line.speaker, ep_id, line, shown_talking_box(line, cast))

    def line_ocr_crop(self, ep_id: str, event: SubtitleEvent | None):
        """What OCR read for a line (band-sized grey image; ocr_crops/, temporary): the line's first reading whose
        text is the line's raw OCR text, else its first reading. None when no crop was saved."""
        from subagent.infra.media import imread
        from subagent.kernel.models import OcrReading
        from subagent.kernel.textutil import normalize_zh
        from subagent.ocr.ocr import crop_path

        work = self.paths.episode_dir(ep_id)
        if event is None or not (work / "ocr_crops").is_dir():
            return None
        inside = [r for r in read_jsonl(work / "ocr_raw.jsonl", OcrReading)
                  if r.kind == "text" and event.start_ms <= r.t_ms < event.end_ms and crop_path(work, r.t_ms).is_file()]
        if not inside:
            return None
        same = [r for r in inside if normalize_zh(r.text) == normalize_zh(event.zh_raw)]
        return imread(crop_path(work, (same or inside)[0].t_ms), gray=True)

    def original_lines(self, ep_id: str) -> dict[str, ReviewedLine]:
        """The pipeline's version of every line, before any review edit (Reset line / Discard review)."""
        from subagent.stages.review import original_draft

        work = self.paths.episode_dir(ep_id)
        review = self.config.review
        return {line.event_id: line for line in original_draft(work, review.predelete_fragments, review.noise_max_han)}

    def save_draft(self, ep_id: str, lines: list[ReviewedLine]) -> None:
        from subagent.stages.review import save_draft

        save_draft(self.paths.episode_dir(ep_id), lines)

    def video_info(self, ep_id: str) -> VideoInfo:
        from subagent.infra.media import probe

        work = self.paths.episode_dir(ep_id)
        if (work / "video.json").is_file():
            return VideoInfo.model_validate_json((work / "video.json").read_text(encoding="utf-8"))
        return probe(Path(self.registry.get(ep_id).source_path))

    def pinyin_engine(self):
        """Glossary-aware pinyin engine, rebuilt when memory changes (loads jieba: call off the UI thread)."""
        from subagent.translation.pinyin_gen import PinyinEngine

        db = self.paths.memory_db
        key = db.stat().st_mtime if db.is_file() else None
        if self._engine is None or key != self._engine_key:
            self._engine = PinyinEngine.from_store(self.store, self.config)
            self._engine_key = key
        return self._engine

    def rule_context(self, ep_id: str | None = None):
        from subagent.translation.evaluate import RuleContext

        return RuleContext(self.config, self.store, self.store.character_ids() | set(self.new_voice_ids(ep_id)))

    def new_voice_ids(self, ep_id: str | None) -> list[str]:
        """Ids a line of the episode may use besides memory's characters (5.15b): its new voices, the NPCs
        created in review, and candidates on probation that may come back in it."""
        return list(self.episode_voices(ep_id))

    def episode_voices(self, ep_id: str | None) -> dict[str, str]:
        """id -> kind: "voice" (found this episode), "review" (created in review), "candidate:<first episode>"."""
        from subagent.memory.characters import draft_voice_ids, load_new_voices

        if not ep_id:
            return {}
        work = self.paths.episode_dir(ep_id)
        out = {v.id: f"candidate:{v.returning_from}" if v.returning_from else "voice" for v in load_new_voices(work)}
        for cid in sorted(draft_voice_ids(work, self.config.voice.new_voice_prefix)):
            out.setdefault(cid, "review")
        ep = self.registry.get(ep_id)
        for c in self.store.returning_candidates(ep.number, self.config.memory.probation_window):
            out.setdefault(c.id, f"candidate:{c.first_episode}")
        return out

    def write_preview(self, ep_id: str, lines: list[ReviewedLine], video: VideoInfo) -> Path:
        from subagent.stages.render import preview_ass

        return preview_ass(self.paths.episode_dir(ep_id), lines, self.config, video.width, video.height)

    def mask_filter(self, video: VideoInfo) -> str:
        from subagent.stages.render import build_mask_filter

        return build_mask_filter(self.config, video.width, video.height)

    # -- settings -----------------------------------------------------------------------------------

    def save_env(self, values: dict[str, str]) -> None:
        from dotenv import set_key

        env = self.paths.env_file
        if not env.exists():
            env.write_text("", encoding="utf-8")
        for key, value in values.items():
            set_key(str(env), key, value, quote_mode="never", encoding="utf-8")
            os.environ[key] = value

    def env_value(self, key: str) -> str:
        return os.environ.get(key, "")
