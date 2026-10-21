from __future__ import annotations

import json
import wave

import numpy as np

from subagent.__main__ import main
from subagent.kernel.models import EditRecord, ReviewedLine
from subagent.kernel.util import write_jsonl
from subagent.memory import bootstrap, dreaming
from subagent.memory.manager import MemoryManager
from subagent.memory.store import MemoryStore
from tests.conftest import make_llm, register_episode, seed_memory

SEED = {
    "characters": [
        {"id": "Lin Yuan", "name_zh": "林渊", "name_vi": "Lâm Uyên", "description": "đệ tử"},
        {"id": "shi_zun", "name_zh": "师尊", "name_vi": "Sư tôn", "description": "sư phụ"},
    ],
    "pronoun_pairs": [
        {"speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "đồ nhi", "address_term": "sư phụ"},
        {"speaker_id": "shi_zun", "listener_id": "ghost", "self_term": "ta", "address_term": "ngươi"},
    ],
    "glossary": [{"zh": "筑基", "vi": "Trúc Cơ", "pinyin": "zhù jī", "type": "realm"}],
}


def _clip(path, freq):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        t = np.arange(16000) / 16000
        w.writeframes((np.sin(2 * np.pi * freq * t) * 8000).astype("<i2").tobytes())


def _fake_embed(samples):
    # embedding from the dominant frequency: same voice → same direction
    spec = np.abs(np.fft.rfft(samples))[:1000]
    v = np.zeros(8, np.float32)
    v[int(np.argmax(spec)) % 8] = 1.0
    return v


def test_bootstrap_seed_and_approve(project):
    config, paths = project
    (paths.bootstrap).mkdir(parents=True)
    (paths.bootstrap / "cast.md").write_text("林渊 (Lâm Uyên) là đệ tử của 师尊.", encoding="utf-8")
    for i in range(3):
        _clip(paths.bootstrap / "voices" / "lin_yuan" / f"{i}.wav", 440)
        _clip(paths.bootstrap / "voices" / "shi_zun" / f"{i}.wav", 440)   # sounds the same → confusable
    llm, _ = make_llm(config, paths, {"utility": lambda m: SEED})
    draft = bootstrap.generate_seed(config, paths, llm, embed=_fake_embed)
    assert [c.id for c in draft.characters] == ["lin_yuan", "shi_zun"]
    assert {g.zh for g in draft.glossary} == {"筑基", "林渊", "师尊"}       # names added to the glossary
    assert any("ghost" in w for w in draft.warnings)
    assert len(draft.voices) == 2 and len(draft.confusable_pairs) == 1

    result = bootstrap.approve_seed(config, paths)
    store = MemoryStore(paths.memory_db)
    assert all(c.locked for c in store.characters())
    assert set(store.voice_bank()) == {"lin_yuan", "shi_zun"}
    assert ("lin_yuan", "shi_zun") in store.confusable_pairs()
    assert any("unknown character" in reason for _, reason in result.rejected)
    assert MemoryManager(paths, config).history()[0].message.startswith("bootstrap")

    _clip(paths.bootstrap / "voices" / "shi_zun" / "0.wav", 3000)
    _clip(paths.bootstrap / "voices" / "shi_zun" / "1.wav", 3000)
    _clip(paths.bootstrap / "voices" / "shi_zun" / "2.wav", 3000)
    bootstrap.update_voices(config, paths, {"shi_zun"}, embed=_fake_embed)
    assert MemoryStore(paths.memory_db).confusable_pairs() == {}


def test_dreaming_proposals_and_apply(project):
    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    write_jsonl(work / "approved.jsonl", [
        ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1, speaker="lin_yuan", listener="shi_zun",
                     zh="我已经筑基了", pinyin="", vi="Đồ nhi đã Xây Nền.", approved=True),
    ])
    write_jsonl(work / "edits.jsonl", [EditRecord(edit_id="ep001:0000:vi", event_id="ep001:0000", field="vi",
                                                  before="Ta đã Trúc Cơ.", after="Đồ nhi đã Xây Nền.")])
    seen = {}

    def utility(messages):
        seen["variable"] = messages[1]["content"]
        return {
            "glossary": [{"zh": "筑基", "vi": "Xây Nền", "reason": "human edit", "evidence": ["ep001:0000:vi"]},
                         {"zh": "下山", "vi": "xuống núi", "reason": "recurring", "evidence": ["ep001:0000"]}],
            "pronoun_pairs": [],
            "style_rules": [{"rule": "Dùng 'đồ nhi' khi đệ tử nói với sư phụ.", "example": "弟子 → đồ nhi"}],
        }

    llm, _ = make_llm(config, paths, {"utility": utility})
    out = dreaming.dream(config, paths, llm)
    assert "lines_not_using_vi" in seen["variable"] and "Xây Nền" in seen["variable"]
    by_key = {i.key: i for i in out.items}
    assert by_key["筑基"].touches_locked and by_key["筑基"].preselected == "reject"
    assert by_key["下山"].preselected == "accept"

    result = dreaming.apply_dream(config, paths, auto=True)
    store = MemoryStore(paths.memory_db)
    assert store.get_row("glossary", "下山")["vi"] == "xuống núi"
    assert store.get_row("glossary", "筑基")["vi"] == "Trúc Cơ"       # locked entry untouched
    assert result.writes == 2
    assert dreaming.load_proposals(paths) is None

    # a second dream sees no new edits
    out2 = dreaming.dream(config, paths, llm)
    assert out2.inputs["edits"] == 0


def test_cli_status_and_add(project, tmp_path, capsys, monkeypatch):
    config, paths = project
    monkeypatch.chdir(paths.root)
    assert main(["status"]) == 0
    assert "No episodes registered" in capsys.readouterr().out

    video = tmp_path / "vids" / "第2集.mp4"
    video.parent.mkdir()
    video.write_bytes(b"v" * 5000)
    monkeypatch.setattr("subagent.infra.media.has_video_stream", lambda p: (True, ""))
    assert main(["add", str(video.parent), "--yes"]) == 0
    assert "registered ep002" in capsys.readouterr().out
    assert main(["--progress", "json", "status", "2", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["id"] == "ep002" and rows[0]["status"] == "new"


def test_cli_errors_are_json_with_codes(project, capsys, monkeypatch):
    config, paths = project
    monkeypatch.chdir(paths.root)
    assert main(["run", "ep009", "--progress", "json"]) == 1
    out = capsys.readouterr().out.strip().splitlines()
    err = json.loads(out[-1])
    assert err["status"] == "error" and err["error_code"] == "episode_not_found"
