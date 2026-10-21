from __future__ import annotations

import wave

import numpy as np

from subagent.kernel.models import PinyinLine, SpeakerCandidates, SubtitleEvent
from subagent.kernel.util import read_jsonl
from subagent.memory.store import Character, GlossaryEntry
from subagent.stages import pinyin_gen
from subagent.stages.windows import build_windows
from subagent.voice import voice
from subagent.workspace.context import EpisodeContext
from tests.conftest import make_episode, make_llm, sample_events, seed_memory, user_json, write_events

# -- pinyin ----------------------------------------------------------------------------------------

def _engine(polyphones=("了", "长", "行")):
    glossary = [GlossaryEntry(zh="林渊", vi="Lâm Uyên", pinyin="Lín Yuān", type="name"),
                GlossaryEntry(zh="筑基", vi="Trúc Cơ", pinyin="zhù jī", type="realm")]
    return pinyin_gen.PinyinEngine(glossary, [Character(id="lin_yuan", name_zh="林渊", name_vi="Lâm Uyên")],
                                   list(polyphones))


def test_pinyin_uses_glossary_and_attaches_punctuation():
    text, _ = _engine().line("林渊，你已经筑基了吗？")
    assert text.startswith("Lín Yuān, ")
    assert "zhù jī" in text
    assert text.endswith("?")
    assert "ma?" in text


def test_pinyin_words_are_joined_within_and_spaced_between():
    text, _ = _engine().line("我们明天去北京")
    assert "wǒmen" in text and "míngtiān" in text and "běijīng" in text


def test_polyphones_outside_known_phrases_are_reported():
    engine = _engine()
    _, positions = engine.line("你了解吗")   # 了 inside the phrase 了解 → known
    assert positions == []
    _, positions = engine.line("好了")       # sentence-final particle outside a phrase → ask
    assert positions == [1]


def test_render_applies_overrides():
    engine = _engine()
    tokens = engine.tokens("好了")
    assert pinyin_gen.PinyinEngine.render(tokens, {1: "liǎo"}).endswith("liǎo")


def test_pinyin_stage_resolves_polyphones_in_one_call(project):
    config, paths = project
    seed_memory(config, paths)
    ctx = EpisodeContext(config, paths, make_episode(paths))
    events = sample_events()
    events.append(SubtitleEvent(id="ep001:0004", start_ms=10000, end_ms=11000, zh_raw="好了", zh="好了", ocr_conf=0.9))
    write_events(ctx.work, events)
    calls = []

    def handler(messages):
        items = user_json(messages, "Polyphones to resolve")
        calls.append(items)
        return {"choices": [{"event_id": it["event_id"], "index": it["index"], "pinyin": it["candidates"][0]}
                            for it in items]}

    ctx.llm_override, _ = make_llm(config, paths, {"utility": handler})
    counts = pinyin_gen.run(ctx)
    assert len(calls) == 1 and counts["polyphones_sent"] >= 1
    lines = {p.event_id: p.pinyin for p in read_jsonl(ctx.artifact("pinyin.jsonl"), PinyinLine)}
    assert "zhù jī" in lines["ep001:0000"]


# -- windows ---------------------------------------------------------------------------------------

def test_windows_split_at_gaps_and_cap(project):
    config, _ = project
    cfg = config.windows.model_copy(update={"gap_ms": 1000, "max_lines": 2, "context_overlap": 1})
    evs = [SubtitleEvent(id=f"e{i}", start_ms=s, end_ms=s + 500, zh_raw="a", zh="a", ocr_conf=1)
           for i, s in enumerate([0, 600, 1200, 5000])]
    ws = build_windows(evs, cfg)
    assert [w.event_ids for w in ws] == [["e0", "e1"], ["e2"], ["e3"]]
    assert ws[1].context_ids == ["e1"] and ws[0].context_ids == []


# -- voice -----------------------------------------------------------------------------------------

def test_classify_status_rules(project):
    config, _ = project
    cfg = config.voice
    assert voice.classify("e", [("a", 0.2), ("b", 0.1)], cfg, set()).status == "unknown"
    assert voice.classify("e", [("a", 0.8), ("b", 0.5)], cfg, set()).status == "fixed"
    assert voice.classify("e", [("a", 0.8), ("b", 0.5)], cfg, {("a", "b")}).status == "confusable"
    assert voice.classify("e", [("a", 0.6), ("b", 0.57)], cfg, set()).status == "confusable"
    assert voice.classify("e", [("a", 0.5), ("b", 0.1)], cfg, set()).status == "confusable"   # below accept


def _write_wav(path, seconds, sr=16000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        t = np.arange(int(seconds * sr)) / sr
        w.writeframes((np.sin(2 * np.pi * 220 * t) * 8000).astype("<i2").tobytes())


def test_voice_stage_with_fake_embedder(project):
    config, paths = project
    seed_memory(config, paths)
    from subagent.memory.manager import MemoryManager

    MemoryManager(paths, config).write_voices({"lin_yuan": (np.array([1, 0, 0], np.float32), 3),
                                               "shi_zun": (np.array([0, 1, 0], np.float32), 3)})
    ctx = EpisodeContext(config, paths, make_episode(paths))
    events = sample_events()
    events[3].end_ms = events[3].start_ms + 200            # too short
    events[2].flags = ["non_dialogue_suspect"]             # skips voice match
    write_events(ctx.work, events)
    _write_wav(ctx.artifact("audio.wav"), 12)
    vectors = iter([np.array([0.9, 0.1, 0], np.float32), np.array([0.1, 0.9, 0], np.float32)])
    counts = voice.run(ctx, embed=lambda clip: voice.l2_normalize(next(vectors)))
    out = {s.event_id: s for s in read_jsonl(ctx.artifact("speakers.jsonl"), SpeakerCandidates)}
    assert out["ep001:0000"].status == "fixed" and out["ep001:0000"].candidates[0][0] == "lin_yuan"
    assert out["ep001:0001"].candidates[0][0] == "shi_zun"
    assert out["ep001:0002"].status == "unknown" and out["ep001:0003"].status == "too_short"
    assert counts["too_short"] == 1


def test_voice_stage_without_voice_bank_needs_no_model(project):
    config, paths = project
    ctx = EpisodeContext(config, paths, make_episode(paths))
    write_events(ctx.work, sample_events())
    _write_wav(ctx.artifact("audio.wav"), 12)
    counts = voice.run(ctx)
    assert counts["unknown"] == 4
