"""End to end through the orchestrator. ffmpeg/OCR-dependent work is stubbed; everything else is real."""

from __future__ import annotations

import io
import json
import wave

import pytest

from subagent.bench.baseline import freeze_finished
from subagent.kernel.errors import OutputExistsError
from subagent.kernel.models import EditRecord, OcrReading, VideoInfo
from subagent.kernel.progress import Progress
from subagent.kernel.util import atomic_write_text, read_jsonl, write_jsonl
from subagent.pipeline import Pipeline, episode_status
from subagent.review import review as review_stage
from subagent.workspace.episodes import Registry
from subagent.workspace.state import load_state
from tests.conftest import make_llm, register_episode, seed_memory, user_json

TEXTS = ["师尊，弟子已经筑基了。", "很好。你果然没让为师失望。", "弟子想下山历练。", "下山？外面很危险。"]
VI = ["Sư phụ, đồ nhi đã Trúc Cơ rồi.", "Tốt. Con không làm vi sư thất vọng.", "Đồ nhi muốn xuống núi lịch luyện.",
      "Xuống núi? Bên ngoài rất nguy hiểm."]
WHO = [("lin_yuan", "shi_zun"), ("shi_zun", "lin_yuan"), ("lin_yuan", "shi_zun"), ("shi_zun", "lin_yuan")]


@pytest.fixture
def calls():
    return {"ingest": 0, "audio": 0, "render": 0}


@pytest.fixture
def stubs(monkeypatch, calls):
    def ingest(ctx):
        calls["ingest"] += 1
        atomic_write_text(ctx.artifact("video.json"), VideoInfo(width=1920, height=1080, duration_ms=12000, fps=25,
                                                                has_audio=True, audio_codec="aac").model_dump_json())
        (ctx.artifact("bands")).mkdir(exist_ok=True)
        (ctx.artifact("bands") / "0.png").write_bytes(b"png")
        (ctx.artifact("changes.jsonl")).write_text("", encoding="utf-8")
        return {"frames": 48}

    def ocr(ctx):
        readings = []
        for i, text in enumerate(TEXTS):
            readings.append(OcrReading(t_ms=i * 3000, kind="text", text=text, confidence=0.95, box_height=0.4,
                                       box_vcenter=0.5, box_hcenter=0.5))
            readings.append(OcrReading(t_ms=i * 3000 + 2500, kind="empty"))
        write_jsonl(ctx.artifact("ocr_raw.jsonl"), readings)
        return {"readings": len(TEXTS)}

    def audio(ctx):
        calls["audio"] += 1
        with wave.open(str(ctx.artifact("audio.wav")), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 16000 * 12)
        return {}

    def render(ctx):
        calls["render"] += 1
        tmp = ctx.artifact("render.tmp.mp4")
        tmp.write_bytes(b"mp4")
        return tmp

    monkeypatch.setattr("subagent.ocr.ingest.run", ingest)
    monkeypatch.setattr("subagent.ocr.ocr.run", ocr)
    monkeypatch.setattr("subagent.voice.audio.run", audio)
    monkeypatch.setattr("subagent.output.render_video", render)


def _handlers():
    def utility(messages):
        system = messages[0]["content"]
        if "correct OCR errors" in system:
            return {"changes": []}
        if "polyphonic" in system:
            items = user_json(messages, "Polyphones to resolve")
            return {"choices": [{"event_id": it["event_id"], "index": it["index"], "pinyin": it["candidates"][0]}
                                for it in items]}
        if "review the whole subtitle script" in system:
            return {"lines": []}
        if "character memory" in system:
            return {"characters": [], "pronouns": []}
        if "story memory" in system:
            return {"summary_sentence": "Lâm Uyên Trúc Cơ và muốn xuống núi.", "characters_introduced": [],
                    "episode_markdown": "# ep001\n## Tóm tắt\nLâm Uyên Trúc Cơ.", "story_so_far": "Lâm Uyên Trúc Cơ."}
        raise AssertionError(system[:80])

    def translator(messages):
        lines = user_json(messages, "Lines to translate")
        out = []
        for x in lines:
            i = int(x["event_id"].split(":")[1])
            out.append({"event_id": x["event_id"], "speaker": WHO[i][0], "listener": WHO[i][1], "speaker_conf": 0.9,
                        "vi": VI[i]})
        return {"lines": out}

    def evaluator(messages):
        lines = user_json(messages, "Lines to evaluate")
        return {"lines": [{"event_id": x["event_id"], "scores": dict.fromkeys(
            ["meaning", "pronouns", "register", "naturalness", "speaker"], 5), "feedback": ""} for x in lines]}

    return {"utility": utility, "translator": translator, "evaluator": evaluator}


def _pipeline(project, stream=None):
    config, paths = project
    llm, clients = make_llm(config, paths, _handlers())
    progress = Progress("json", stream=stream or io.StringIO())
    return Pipeline(config, paths, progress=progress, llm=llm, after_finish=[freeze_finished]), clients, progress


def test_human_mode_then_finish_review(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    stream = io.StringIO()
    pipe, clients, _ = _pipeline(project, stream)

    assert pipe.run("ep001", mode="human") == "awaiting_review"
    reg = Registry(paths)
    assert reg.get("ep001").status == "awaiting_review"
    work = paths.episode_dir("ep001")
    draft = review_stage.load_draft(work)
    assert len(draft) == 4 and draft[0].vi == VI[0] and draft[0].pinyin
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert {"stage", "status", "done", "total", "cost", "message", "error_code"} <= set(events[0])

    # resume: nothing reruns, no LLM calls
    n_calls = sum(len(c.calls) for c in clients.values())
    stream2 = io.StringIO()
    pipe2, clients2, _ = _pipeline(project, stream2)
    pipe2.run("ep001", mode="human")
    statuses = {e["stage"]: e["status"] for e in map(json.loads, stream2.getvalue().splitlines()) if e["status"] != "info"}
    assert all(statuses[s] == "skipped" for s in ("ingest", "ocr", "translate", "review"))
    assert sum(len(c.calls) for c in clients2.values()) == 0 and calls["ingest"] == 1
    assert n_calls > 0

    for line in draft:
        line.approved = True
    draft[1].vi = "Tốt lắm. Con không làm vi sư thất vọng."
    review_stage.save_draft(work, draft)
    pipe.config.baseline.name = "base1"
    assert pipe.finish_review("ep001") == "done"
    frozen = paths.work / "_baseline" / "base1"
    assert (frozen / "ep001" / "approved.jsonl").read_bytes() == (work / "approved.jsonl").read_bytes()
    manifest = json.loads((frozen / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["episodes"]["ep001"]["memory_commit"] and "edits.jsonl" in manifest["episodes"]["ep001"]["files"]

    ep = reg.get("ep001")
    assert ep.status == "done" and ep.output_path.endswith("ep01_vi.mp4")
    assert (paths.root.parent / "output" / "ep01_vi.mp4").read_bytes() == b"mp4"
    assert len(read_jsonl(work / "edits.jsonl", EditRecord)) == 1
    assert not (work / "bands").exists() and (work / "approved.jsonl").exists()
    state = load_state(work, "ep001")
    assert state.stages["ingest"].status == "purged" and state.stages["memory"].status == "done"
    assert "Voice match" in (work / "report.md").read_text(encoding="utf-8")
    assert episode_status(paths, ep)["stages"]["render"] == "done"


def test_auto_mode_end_to_end_and_output_conflict(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    pipe, _, _ = _pipeline(project)
    assert pipe.run("1", mode="auto") == "done"
    assert calls["render"] == 1
    with pytest.raises(OutputExistsError):
        pipe.render("ep001", on_exists="fail")
    assert calls["render"] == 1          # checked before rendering: nothing wasted
    final = pipe.render("ep001", on_exists="keep_both")
    assert final.name == "ep01_vi (2).mp4"


def test_purged_stage_is_regenerated_when_needed(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    pipe, _, _ = _pipeline(project)
    pipe.run("ep001", mode="auto")
    assert not paths.episode_dir("ep001").joinpath("audio.wav").exists()
    pipe.run("ep001", mode="auto", force_stage="voice", on_exists="overwrite")
    assert calls["audio"] == 2 and calls["ingest"] == 1


def test_missing_source_marks_episode(project, stubs, monkeypatch):
    from pathlib import Path

    import subagent.ocr.ingest as ingest
    from subagent.kernel.errors import SourceMissingError

    config, paths = project
    ep = register_episode(paths, 1)
    Path(ep.source_path).unlink()
    stub = ingest.run

    def needs_source(ctx):
        ctx.require_source()
        return stub(ctx)

    monkeypatch.setattr(ingest, "run", needs_source)
    pipe, _, _ = _pipeline(project)
    with pytest.raises(SourceMissingError):
        pipe.run("ep001", mode="human")
    assert Registry(paths).get("ep001").status == "missing"


def test_batch_runs_in_episode_order_skips_finished_and_stops_on_failure(project, stubs, calls, monkeypatch):
    config, paths = project
    seed_memory(config, paths)
    for n in (3, 1, 2, 4):
        register_episode(paths, n)
    stream = io.StringIO()
    pipe, _, _ = _pipeline(project, stream)
    assert pipe.run("1", mode="auto") == "done"
    ran = []
    real_run = Pipeline.run

    def run(self, ep_ref, **kw):
        ran.append(ep_ref)
        if ep_ref == "ep003":
            raise RuntimeError("disk full")
        return real_run(self, ep_ref, **kw)

    monkeypatch.setattr(Pipeline, "run", run)
    items = pipe.run_batch(["ep004", "ep003", "ep002", "ep001"], mode="auto")
    assert [(i.episode_id, i.status) for i in items] == [("ep001", "skipped"), ("ep002", "done"),
                                                         ("ep003", "failed"), ("ep004", "not_run")]
    assert ran == ["ep002", "ep003"]                                  # episode order; stopped after the failure
    assert items[2].reason == "disk full"
    events = [json.loads(x) for x in stream.getvalue().splitlines() if x.strip()]
    assert any(e["stage"] == "batch" and e["status"] == "progress" and e["message"] == "ep002 (2/4)" for e in events)

    ran.clear()
    items = pipe.run_batch(["ep003", "ep004"], mode="auto", keep_going=True)
    assert ran == ["ep003", "ep004"] and [i.status for i in items] == ["failed", "done"]


def test_batch_cost_limit(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    register_episode(paths, 2)
    pipe, _, _ = _pipeline(project)
    items = pipe.run_batch(["ep001", "ep002"], mode="human", max_total_cost=0.0)
    assert [(i.episode_id, i.status) for i in items] == [("ep001", "not_run"), ("ep002", "not_run")]
    items = pipe.run_batch(["ep001", "ep002"], mode="human")
    assert [i.status for i in items] == ["awaiting_review", "awaiting_review"]


def test_rerun_processes_a_finished_episode_again(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    pipe, _, _ = _pipeline(project)
    pipe.run("ep001", mode="human")
    work = paths.episode_dir("ep001")
    draft = review_stage.load_draft(work)
    for line in draft:
        line.approved = True
    review_stage.save_draft(work, draft)
    assert pipe.finish_review("ep001") == "done"

    stream = io.StringIO()
    pipe2, _, _ = _pipeline(project, stream)
    assert pipe2.run("ep001", mode="human", rerun=True) == "awaiting_review"
    statuses = {e["stage"]: e["status"] for e in map(json.loads, stream.getvalue().splitlines()) if e["status"] != "info"}
    assert statuses["ocr"] == "skipped"                                   # video-only stages: unchanged, kept
    assert all(statuses[s] == "done" for s in ("ocr_fix", "voice", "translate", "script_review", "review"))
    assert Registry(paths).get("ep001").status == "awaiting_review"
    assert not any(x.approved for x in review_stage.load_draft(work))     # the review starts over


def test_batch_rerun_includes_finished_episodes(project, stubs, calls):
    config, paths = project
    seed_memory(config, paths)
    register_episode(paths, 1)
    pipe, _, _ = _pipeline(project)
    pipe.run("ep001", mode="human")
    assert pipe.run_batch(["ep001"], mode="human")[0].status == "skipped"
    assert pipe.run_batch(["ep001"], mode="human", rerun=True)[0].status == "awaiting_review"
