"""Character identification off (5.11a): no voice / cast / sprite stages, no speakers, one default pronoun pair in
the prompts, and no characters, pronoun pairs or lifecycle written to memory."""

from __future__ import annotations

import pytest
import yaml

from subagent import series as sr
from subagent.config import ShowConfig, load_config, parse_config
from subagent.kernel.errors import ConfigError, SubagentError
from subagent.kernel.models import LineTranslation
from subagent.kernel.util import read_jsonl
from subagent.memory.store import MemoryStore
from subagent.stages import review as review_stage
from subagent.stages.translate import mode_prompt
from subagent.state import load_state
from tests.conftest import register_episode, seed_memory, user_json
from tests.test_pipeline import VI, WHO, _handlers, _pipeline, calls, stubs  # noqa: F401 - fixtures

OFF = ShowConfig(character_identification=False, self_term=" ta ", address_term="ngươi")


def test_off_needs_the_default_pair(project):
    config, _ = project
    data = config.model_dump(mode="json")
    data["show"] |= {"character_identification": False, "self_term": "ta"}
    with pytest.raises(ConfigError, match="default pronoun pair"):
        parse_config(data)
    data["show"]["address_term"] = "ngươi"
    assert parse_config(data).show.self_term == "ta"
    assert OFF.self_term == "ta"                                   # trimmed


def test_mode_blocks_in_prompts(project):
    config, _ = project
    text = "a\n<!-- if:identify -->\nmatrix\n<!-- /if -->\n<!-- if:default_pair -->\nuse {{self_term}} / " \
           "{{address_term}}\n<!-- /if -->\nb\n"
    assert mode_prompt(text, config) == "a\nmatrix\nb\n"
    off = config.model_copy(update={"show": OFF})
    assert mode_prompt(text, off) == "a\nuse ta / ngươi\nb\n"
    with pytest.raises(SubagentError):
        mode_prompt("<!-- if:other -->\nx\n<!-- /if -->\n", config)


def test_off_skips_identification_and_learns_no_characters(project, stubs, calls):  # noqa: F811
    config, paths = project
    config.show = OFF
    seed_memory(config, paths)
    register_episode(paths, 1)
    handlers = _handlers()
    seen: dict = {}

    def translator(messages):
        seen["system"] = messages[0]["content"]
        seen["prefix"] = "\n".join(m["content"] for m in messages[:-1])
        lines = user_json(messages, "Lines to translate")
        seen["lines"] = lines
        out = []
        for x in lines:                 # a model that still names speakers and proposes a pair: both ignored
            i = int(x["event_id"].split(":")[1])
            out.append({"event_id": x["event_id"], "speaker": WHO[i][0], "listener": WHO[i][1], "vi": VI[i],
                        "proposals": [{"kind": "pronoun_pair", "evidence": [x["event_id"]], "payload": {
                            "speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "ta",
                            "address_term": "ngươi", "context": "angry"}}]})
        return {"lines": out}

    def evaluator(messages):
        seen["eval_system"] = messages[0]["content"]
        lines = user_json(messages, "Lines to evaluate")
        seen["eval_lines"] = lines
        return {"lines": [{"event_id": x["event_id"], "scores": dict.fromkeys(
            ["meaning", "pronouns", "register", "naturalness", "speaker"], 5) | {"speaker": 1}, "feedback": ""}
            for x in lines]}

    handlers |= {"translator": translator, "evaluator": evaluator}
    from tests.conftest import make_llm

    llm, _ = make_llm(config, paths, handlers)
    pipe, _, _ = _pipeline(project)
    pipe.llm = llm
    assert pipe.run("ep001", mode="human") == "awaiting_review"

    work = paths.episode_dir("ep001")
    state = load_state(work, "ep001")
    assert all(state.stages[s].status == "off" for s in ("audio", "voice", "cast", "sprite"))
    assert calls["audio"] == 0 and not (work / "speakers.jsonl").exists()
    assert "## Speaker rules" not in seen["system"] and "as `ta`" in seen["system"]
    assert "Pronoun matrix" not in seen["prefix"] and "Lâm Uyên" in seen["prefix"]   # characters still named
    assert all("speaker_status" not in x for x in seen["lines"])
    assert all("speaker" not in x and "voice_status" not in x for x in seen["eval_lines"])
    assert "`ta` for the speaker" in seen["eval_system"]
    translations = read_jsonl(work / "translations.jsonl", LineTranslation)
    assert all(t.speaker is None and t.listener is None for t in translations)
    assert all("retry_cap" not in t.flags and "low_speaker_conf" not in t.flags for t in translations)  # speaker=1

    draft = review_stage.load_draft(work)
    for line in draft:
        line.approved = True
    review_stage.save_draft(work, draft)
    assert pipe.finish_review("ep001") == "done"
    store = MemoryStore(paths.memory_db)
    assert {(p.speaker_id, p.listener_id, p.context) for p in store.pronoun_pairs()} == {
        ("lin_yuan", "shi_zun", ""), ("shi_zun", "lin_yuan", "")}                      # the seed only
    assert store.character_ids() == {"lin_yuan", "shi_zun"}
    state = load_state(work, "ep001")
    assert "voices" not in state.stages and "sprites" not in state.stages


def test_turning_it_on_again_runs_the_stages(project, stubs, calls):  # noqa: F811
    config, paths = project
    config.show = OFF
    seed_memory(config, paths)
    register_episode(paths, 1)
    pipe, _, _ = _pipeline(project)
    pipe.run("ep001", mode="human")
    config.show = ShowConfig()
    pipe.run("ep001", mode="human")
    state = load_state(paths.episode_dir("ep001"), "ep001")
    assert state.stages["voice"].status == "done" and calls["audio"] == 1
    assert (paths.episode_dir("ep001") / "speakers.jsonl").is_file()


def test_new_series_asks_how_pronouns_are_decided(project, capsys):
    from subagent.__main__ import main

    _, paths = project
    with pytest.raises(SubagentError, match="default pronoun pair"):
        sr.add(paths.root, "show-c", "Show C", identify=False, self_term="ta")
    assert main(["series", "add", "show-b", "--name", "Show B"]) == 2            # neither choice given
    assert "--pronouns" in capsys.readouterr().out
    assert main(["series", "add", "show-b", "--name", "Show B", "--pronouns", "ta", "ngươi"]) == 0
    own = yaml.safe_load((sr.series_root(paths.root) / "show-b" / "series.yaml").read_text(encoding="utf-8"))
    assert own["show"] == {"name": "Show B", "genre_register": "co_trang_tien_hiep",
                                "character_identification": False, "self_term": "ta", "address_term": "ngươi"}
    cfg, _ = load_config(paths.root, "show-b")
    assert not cfg.show.character_identification and cfg.show.address_term == "ngươi"
