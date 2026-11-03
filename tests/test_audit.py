"""Audit: reproducible stratified samples, disagreement lines, and accuracy estimates (6.11)."""

from __future__ import annotations

import pytest

from subagent.bench import audit
from subagent.kernel.models import (
    AuditMark,
    CastDetection,
    CastLine,
    EpisodeState,
    ReviewedLine,
    SpeakerCandidates,
)
from subagent.kernel.util import write_jsonl
from subagent.workspace.state import save_state
from tests.conftest import register_episode


def _episode(paths, number: int, n: int = 100, flagged_every: int = 5, mode: str = "auto"):
    ep = register_episode(paths, number)
    work = paths.episode_dir(ep.id)
    work.mkdir(parents=True, exist_ok=True)
    lines = [ReviewedLine(event_id=f"{ep.id}:{i:04d}", start_ms=i * 1000, end_ms=i * 1000 + 900, speaker="lin_yuan",
                          listener=None, zh="字", pinyin="", vi="x", approved=True,
                          flags=["low_speaker_conf"] if i % flagged_every == 0 else ["cps_exceeded"], deleted=i == 99)
             for i in range(n)]
    write_jsonl(work / "approved.jsonl", lines)
    save_state(work, EpisodeState(episode_id=ep.id, mode=mode))
    return ep, work


def test_sample_is_stratified_reproducible_and_adds_disagreements(project):
    config, paths = project
    ep, work = _episode(paths, 1)
    write_jsonl(work / "speakers.jsonl", [SpeakerCandidates(event_id=f"{ep.id}:0003", status="fixed",
                                                            candidates=[("shi_zun", 0.8)])])
    write_jsonl(work / "cast.jsonl", [CastLine(event_id=f"{ep.id}:0007", talking=0, detections=[
        CastDetection(index=0, box=[0, 0, 1, 1], score=0.5, label="c", character="shi_zun")])])
    s1 = audit.draw_sample(config, paths, ep.id)
    s2 = audit.draw_sample(config, paths, ep.id)
    assert [x.event_id for x in s1] == [x.event_id for x in s2]                  # same episode, same sample
    random = [x for x in s1 if x.kind == "random"]
    assert len(random) == 20 and sum(x.flagged for x in random) == 4              # 20 of 99 lines flagged: 4 of 20
    assert f"{ep.id}:0099" not in {x.event_id for x in s1}                        # deleted lines are not output
    dis = {x.event_id: x.disagreement for x in s1 if x.disagreement}
    assert dis[f"{ep.id}:0003"] == ["voice: shi_zun"] and dis[f"{ep.id}:0007"] == ["talking on screen: shi_zun"]


def test_small_strata_get_their_minimum(project):
    config, paths = project
    ep, _ = _episode(paths, 2, n=40, flagged_every=40)                             # only 1 flagged line
    random = [x for x in audit.draw_sample(config, paths, ep.id) if x.kind == "random"]
    assert sum(x.flagged for x in random) == 1 and len(random) == 20


def test_report_estimates_accuracy_by_stratum(project):
    config, paths = project
    ep, work = _episode(paths, 1)
    sample = audit.draw_sample(config, paths, ep.id)
    marks = {}
    for x in sample:
        wrong = x.flagged                      # every flagged line has a wrong speaker, unflagged ones are right
        marks[x.event_id] = AuditMark(event_id=x.event_id, speaker=not wrong, ocr=True, translation=True,
                                      na=["pronouns"])
    audit.save_marks(work, marks)
    r = audit.build_report(config, paths, [ep.id])
    assert r.aspects["speaker"].errors == pytest.approx(20 / 99)                  # weighted by the strata sizes
    assert r.aspects["ocr"].errors == 0 and r.aspects["ocr"].high > 0              # a clean sample still has a range
    assert r.aspects["pronouns"].checked == 0                                      # all n/a: no estimate
    assert r.flagged.errors == 1.0 and r.unflagged.errors == 0.0
    text = audit.render_report(r)
    assert "Speaker: 80%" in text and "Pronouns (xưng hô): n/a" in text
    _, path = audit.write_report(config, paths, [ep.id])
    assert path.is_file() and (path.parent / "summary.json").is_file()


def test_marks_keep_not_applicable_apart_from_unmarked(project):
    config, paths = project
    _, work = _episode(paths, 1, n=5)
    audit.save_marks(work, {"a": AuditMark(event_id="a", na=["pronouns"]), "b": AuditMark(event_id="b")})
    loaded = audit.load_marks(work)
    assert set(loaded) == {"a"} and loaded["a"].na == ["pronouns"] and loaded["a"].pronouns is None


def test_human_reviewed_episodes_are_not_audited_by_default(project):
    config, paths = project
    ep, work = _episode(paths, 3, mode="human")
    assert audit.draw_sample(config, paths, ep.id) == [] and not audit.load_sample(work)
    config.audit.include_human = True
    assert audit.draw_sample(config, paths, ep.id)
    config.audit.include_human = False
    assert audit.build_report(config, paths, [ep.id]).episodes == []      # an old sample is not counted either


def test_gold_answers_and_benchmark(project):
    import json

    from subagent.bench.benchmark import benchmark_episodes, run_benchmark
    from subagent.kernel.models import LineTranslation

    config, paths = project
    ep, work = _episode(paths, 1, n=20)
    other, other_work = _episode(paths, 2, n=5, mode="human")
    write_jsonl(other_work / "edits.jsonl", [])                      # reviewer context to copy into the sandbox
    (work / "events.jsonl").write_text("", encoding="utf-8")
    sample = audit.draw_sample(config, paths, ep.id)
    ids = [s.event_id for s in sample]
    marks = {ids[0]: AuditMark(event_id=ids[0], speaker=True, speaker_value="lin_yuan"),
             ids[1]: AuditMark(event_id=ids[1], speaker=False, correct_speaker="shi_zun"),
             ids[2]: AuditMark(event_id=ids[2], speaker=False),                     # no answer: not gold
             ids[3]: AuditMark(event_id=ids[3], na=["speaker"])}
    audit.save_marks(work, marks)
    assert audit.gold_speakers(work) == {ids[0]: "lin_yuan", ids[1]: "shi_zun"}
    assert audit.missing_answers(work) == 1 and benchmark_episodes(paths) == [ep.id]
    before = (work / "approved.jsonl").read_text(encoding="utf-8")
    ran = []

    def fake_stage(name, ctx):
        ran.append((name, ctx.work))
        if name == "translate":                      # today's system now gets the second line right
            write_jsonl(ctx.artifact("translations.jsonl"), [
                LineTranslation(event_id=e, speaker="shi_zun" if e == ids[1] else "lin_yuan", listener=None,
                                speaker_conf=0.5, vi="x", attempts=1) for e in ids])

    r = run_benchmark(config, paths, label="test", stage_runner=fake_stage)
    assert [n for n, _ in ran] == ["audio", "voice", "cast", "windows", "translate"]
    assert all(str(w).startswith(str(paths.work / "_benchmark")) for _, w in ran)   # sandboxed
    assert (work / "approved.jsonl").read_text(encoding="utf-8") == before            # real episode untouched
    score = r.episodes[0]
    assert (score.gold, score.right, score.before_right) == (2, 2, 1)
    assert score.changed == [{"event_id": ids[1], "before": "lin_yuan", "now": "shi_zun", "gold": "shi_zun"}]
    sandbox_other = paths.work / "_benchmark" / pathlib_name(r.folder) / other.id / "edits.jsonl"
    assert sandbox_other.is_file()
    history = [json.loads(x) for x in (paths.work / "_benchmark" / "history.jsonl").read_text(encoding="utf-8").splitlines()]
    assert history[-1]["label"] == "test" and history[-1]["episodes"] == [ep.id]


def pathlib_name(folder: str) -> str:
    from pathlib import Path

    return Path(folder).name


def test_new_character_without_id_means_blank_is_right(project):
    config, paths = project
    ep, work = _episode(paths, 1, n=20)
    ids = [s.event_id for s in audit.draw_sample(config, paths, ep.id)]
    audit.save_marks(work, {ids[0]: AuditMark(event_id=ids[0], speaker=False, correct_speaker=audit.NO_ID_YET)})
    assert audit.gold_speakers(work) == {ids[0]: None} and audit.missing_answers(work) == 0


def test_score_episode_strata_and_disagreements():
    from subagent.bench.benchmark import _score_episode
    from subagent.kernel import AuditSample

    def line(e: str, speaker: str, flags: list[str] | None = None) -> ReviewedLine:
        return ReviewedLine(event_id=e, start_ms=0, end_ms=1, speaker=speaker, listener=None, zh="字", pinyin="zì",
                            vi="x", flags=flags or [])

    audited = {"a": line("a", "lin_yuan"), "b": line("b", "lin_yuan", ["speaker_invalid"]),
               "c": line("c", "lin_yuan", ["cps_exceeded"]), "d": line("d", "shi_zun")}
    sample = {"a": AuditSample(event_id="a", kind="random", flagged=False),
              "b": AuditSample(event_id="b", kind="random", flagged=True),
              "d": AuditSample(event_id="d", kind="disagreement", flagged=False)}
    gold = {"a": "lin_yuan", "b": "shi_zun", "d": "shi_zun", "e": "lin_yuan"}      # e: gold but never audited
    predicted = {"a": "lin_yuan", "b": "shi_zun", "d": "lin_yuan", "e": "lin_yuan"}
    t = _score_episode("ep001", gold, predicted, audited, sample, ["cps_exceeded"])
    assert (t.score.gold, t.score.right, t.score.before_right) == (4, 3, 2)
    assert [c["event_id"] for c in t.score.changed] == ["b", "d", "e"]
    assert t.cells == [(1, 1, 0), (3, 1, 0)]                # flagged: b only (c's flag is ignored); unflagged: a, c, d
    assert t.before_cells == [(1, 1, 1), (3, 1, 0)]         # b was wrong as audited
    assert (t.disagreement_wrong, t.disagreement_lines) == (1, 1)
