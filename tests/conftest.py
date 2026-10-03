"""Shared fixtures: a throwaway project folder and a fake OpenAI-compatible client (NFR-M3)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from subagent.config import Config, Paths, load_config
from subagent.llm import LLMClient
from subagent.models import Episode, SubtitleEvent
from subagent.util import write_jsonl

REPO = Path(__file__).resolve().parent.parent

Handler = Callable[[list[dict]], object]


class FakeCompletions:
    def __init__(self, handler: Handler):
        self.handler = handler
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        out = self.handler(kwargs["messages"])
        if isinstance(out, BaseException):
            raise out
        content = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=200, prompt_cache_hit_tokens=600)
        choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=usage)


class FakeClient:
    def __init__(self, handler: Handler):
        self.completions = FakeCompletions(handler)
        self.chat = SimpleNamespace(completions=self.completions)

    @property
    def calls(self) -> list[dict]:
        return self.completions.calls


def user_json(messages: list[dict], header: str) -> list | dict:
    """The JSON block that follows `header` in the user message."""
    text = messages[-1]["content"] if messages[-1]["role"] == "user" else messages[1]["content"]
    for m in messages:
        if m["role"] == "user" and header in m["content"]:
            text = m["content"]
    start = text.index(header) + len(header)
    rest = text[start:].lstrip(":\n ")
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(rest)
    return value


def make_llm(config: Config, paths: Paths, handlers: dict[str, Handler], *, cost_path: Path | None = None,
             budget: float | None = None) -> tuple[LLMClient, dict[str, FakeClient]]:
    clients = {role: FakeClient(h) for role, h in handlers.items()}
    llm = LLMClient(config, paths, cost_path=cost_path, budget=budget, clients=clients, sleep=lambda s: None)
    return llm, clients


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> tuple[Config, Paths]:
    root = tmp_path / "project dự án 项目"   # spaces, Vietnamese and Chinese in the path (NFR-S3)
    root.mkdir()
    data = yaml.safe_load((REPO / "config.yaml").read_text(encoding="utf-8"))
    out = tmp_path / "output"
    out.mkdir()
    # Every location must live inside tmp_path: the user's config may point at real folders
    # (e.g. paths.work_dir: E:/Video Data/Raw), and tests must never write there.
    data["output"]["folder"] = str(out)
    data.setdefault("paths", {})["work_dir"] = "work"
    data.setdefault("render", {})["font_dir"] = "fonts"
    # model stages that would load real models are off; their own tests turn them on with fakes
    data.setdefault("cast", {})["enabled"] = False
    # OCR pre-processing needs a calibrated series style; tests that cover it switch it on themselves
    for key in ("preprocess", "recognize", "mask_image", "mask_scale"):
        data.setdefault("ocr", {}).pop(key, None)
    data.setdefault("video", {})["band_frames"] = 1
    data["llm"]["prices"] = {"deepseek-chat": {"input": 0.27, "input_cached": 0.07, "output": 1.1},
                             "qwen-plus": {"input": 0.4, "input_cached": 0.1, "output": 1.2}}
    (root / "config.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    shutil.copytree(REPO / "prompts", root / "prompts")
    (root / "fonts").mkdir()
    (root / "fonts" / "Dummy.ttf").write_bytes(b"not a real font")
    monkeypatch.setenv("SUBAGENT_ROOT", str(root))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")          # tests never download models
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setenv("QWEN_API_KEY", "test")
    config, paths = load_config(root)
    tmp = tmp_path.resolve()
    for name in ("work", "data", "memory", "cache", "fonts", "episodes_index"):
        location = getattr(paths, name).resolve()
        assert location.is_relative_to(tmp), f"test path {name} escapes the temp folder: {location}"
    assert Path(config.output.folder).resolve().is_relative_to(tmp)
    return config, paths


def make_episode(paths: Paths, number: int = 1, source: Path | None = None) -> Episode:
    src = source or (paths.root / f"ep{number:02d}.mp4")
    if not src.exists():
        src.write_bytes(b"\x00" * 2048 + str(number).encode())
    from subagent.episodes import fingerprint

    return Episode(id=f"ep{number:03d}", number=number, source_path=str(src), source_size=src.stat().st_size,
                   source_mtime=src.stat().st_mtime, source_fingerprint=fingerprint(src), added_at="2026-01-01")


def register_episode(paths: Paths, number: int = 1) -> Episode:
    from subagent.episodes import Registry

    ep = make_episode(paths, number)
    reg = Registry(paths)
    reg._mutate(lambda eps: eps.append(ep))
    return ep


def sample_events(episode_id: str = "ep001") -> list[SubtitleEvent]:
    texts = ["师尊，弟子已经筑基了。", "很好。你果然没让为师失望。", "弟子想下山历练。", "下山？外面很危险。"]
    events = []
    for i, zh in enumerate(texts):
        events.append(SubtitleEvent(id=f"{episode_id}:{i:04d}", start_ms=i * 2500, end_ms=i * 2500 + 2200,
                                    zh_raw=zh, zh=zh, ocr_conf=0.95, box_height=0.4, box_vcenter=0.5, box_hcenter=0.5))
    return events


def write_events(work: Path, events: list[SubtitleEvent], name: str = "events.jsonl") -> None:
    work.mkdir(parents=True, exist_ok=True)
    write_jsonl(work / name, events)


def seed_memory(config: Config, paths: Paths) -> None:
    """Characters, glossary and pronoun pairs used across tests (written the proper way: bootstrap source)."""
    from subagent.memory.manager import MemoryManager
    from subagent.models import MemoryProposal

    m = MemoryManager(paths, config)
    m.ensure_repo()
    props = [
        MemoryProposal(kind="character", source="bootstrap",
                       payload={"id": "lin_yuan", "name_zh": "林渊", "name_vi": "Lâm Uyên", "description": "đệ tử"}),
        MemoryProposal(kind="character", source="bootstrap",
                       payload={"id": "shi_zun", "name_zh": "师尊", "name_vi": "Sư tôn", "description": "sư phụ"}),
        MemoryProposal(kind="glossary", source="bootstrap",
                       payload={"zh": "筑基", "vi": "Trúc Cơ", "pinyin": "zhù jī", "type": "realm"}),
        MemoryProposal(kind="glossary", source="bootstrap",
                       payload={"zh": "林渊", "vi": "Lâm Uyên", "pinyin": "Lín Yuān", "type": "name"}),
        MemoryProposal(kind="pronoun_pair", source="bootstrap",
                       payload={"speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "đồ nhi",
                                "address_term": "sư phụ"}),
        MemoryProposal(kind="pronoun_pair", source="bootstrap",
                       payload={"speaker_id": "shi_zun", "listener_id": "lin_yuan", "self_term": "vi sư",
                                "address_term": "con"}),
    ]
    m.apply(props)
    m.commit("seed")
