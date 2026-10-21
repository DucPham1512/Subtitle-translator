"""Several series in one project: data/series/<slug>/, series.yaml overrides, series notes in prompts, settings
written to the right file, migrating the single-series layout, renaming, choosing the default."""

from __future__ import annotations

import pytest
import yaml

from subagent import series as sr
from subagent.config import load_config, update_config_values
from subagent.kernel.errors import ConfigError, SubagentError
from subagent.llm import SERIES_NOTES, load_prompt
from subagent.memory.store import MemoryStore
from subagent.pipeline import _prompt_hash
from tests.conftest import seed_memory


def test_a_new_series_has_its_own_folders_settings_and_font(project):
    config, paths = project
    folder = sr.add(paths.root, "show-b", "Show B", "co_trang_tien_hiep")
    cfg, sp = load_config(paths.root, "show-b")
    assert cfg.show.name == "Show B" and cfg.series.default == "show-b"
    assert sp.data == folder and sp.memory == folder / "memory" and sp.bootstrap == folder / "bootstrap"
    assert sp.episodes_index == folder / "episodes" / "index.json" and sp.card_pins == folder / "character_cards"
    assert sp.work == paths.work / "show-b"                      # no work_dir of its own: a subfolder
    assert sp.fonts == folder / "fonts" and any(f.suffix == ".ttf" for f in sp.fonts.iterdir())
    assert sp.card_cache == paths.root / "cache" / "character_cards" / "show-b"
    assert sp.prompts == paths.prompts                         # general prompts stay shared
    assert cfg.llm.providers.keys() == config.llm.providers.keys()    # shared settings still apply
    with pytest.raises(SubagentError):
        sr.add(paths.root, "show-b", "again")
    with pytest.raises(SubagentError):
        sr.check_slug("Show B")
    with pytest.raises(ConfigError):
        load_config(paths.root, "no-such-show")


def test_series_yaml_overrides_sections_and_its_own_work_dir(project, tmp_path):
    _, paths = project
    folder = sr.add(paths.root, "show-b", "Show B", work_dir=str(tmp_path / "elsewhere"))
    data = yaml.safe_load((folder / "series.yaml").read_text(encoding="utf-8"))
    data["video"] = {"subtitle_band": {"top": 0.7, "bottom": 0.9, "left": 0.1, "right": 0.9}}
    (folder / "series.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    cfg, sp = load_config(paths.root, "show-b")
    assert cfg.video.subtitle_band.top == 0.7 and cfg.video.sample_fps == load_config(paths.root)[0].video.sample_fps
    assert sp.work == tmp_path / "elsewhere"


def test_series_notes_follow_the_general_prompt(project):
    _, paths = project
    folder = sr.add(paths.root, "show-b", "Show B")
    _, sp = load_config(paths.root, "show-b")
    plain, plain_hash = load_prompt(sp, "script_review_system"), _prompt_hash(sp, "script_review_system")
    assert SERIES_NOTES not in plain
    (folder / "prompts" / "script_review_system.md").write_text("This font draws 了 like 7.", encoding="utf-8")
    text = load_prompt(sp, "script_review_system")
    assert text.startswith(plain.rstrip()) and text.rstrip().endswith(f"{SERIES_NOTES}\n\nThis font draws 了 like 7.")
    assert _prompt_hash(sp, "script_review_system") != plain_hash      # the stage reruns when the notes change


def test_settings_go_to_the_series_or_the_shared_file(project, monkeypatch):
    _, paths = project
    folder = sr.add(paths.root, "show-b", "Show B")
    monkeypatch.setenv("SUBAGENT_SERIES", "show-b")
    update_config_values(paths.root, {"video.sample_fps": 3, "budget.max_cost_per_episode": 2.5})
    own = yaml.safe_load((folder / "series.yaml").read_text(encoding="utf-8"))
    shared = yaml.safe_load((paths.root / "config.yaml").read_text(encoding="utf-8"))
    assert own["video"]["sample_fps"] == 3 and "video" not in shared or shared["video"].get("sample_fps") != 3
    assert shared["budget"]["max_cost_per_episode"] == 2.5 and "budget" not in own
    cfg, _ = load_config(paths.root)
    assert cfg.video.sample_fps == 3 and cfg.budget.max_cost_per_episode == 2.5


def test_migrate_names_the_single_series_layout(project):
    config, paths = project
    seed_memory(config, paths)
    (paths.root / "data" / "bootstrap").mkdir(parents=True, exist_ok=True)
    (paths.root / "data" / "bootstrap" / "cast.md").write_text("cast", encoding="utf-8")
    before = (paths.root / "config.yaml").read_text(encoding="utf-8")
    folder = sr.migrate(paths.root, "one")
    assert not (paths.root / "data" / "memory").exists() and (folder / "memory" / "memory.db").is_file()
    assert (folder / "bootstrap" / "cast.md").is_file() and (folder / "fonts").is_dir()
    shared = yaml.safe_load((paths.root / "config.yaml").read_text(encoding="utf-8"))
    own = yaml.safe_load((folder / "series.yaml").read_text(encoding="utf-8"))
    assert shared["series"]["default"] == "one" and "show" not in shared and "video" not in shared
    assert set(own) <= set(sr.SERIES_SECTIONS) and "show" in own and "llm" in shared
    cfg, sp = load_config(paths.root)
    assert sp.series == "one" and sp.work == paths.work                 # its work_dir moved with it: unchanged
    assert {c.id for c in MemoryStore(sp.memory_db).characters()} == {"lin_yuan", "shi_zun"}
    assert cfg.model_dump(exclude={"series"}) == config.model_dump(exclude={"series"})   # same effective settings
    assert "llm" in before
    with pytest.raises(SubagentError):
        sr.migrate(paths.root, "two")                                   # nothing left to migrate


def test_rename_and_default(project):
    config, paths = project
    seed_memory(config, paths)
    sr.migrate(paths.root, "one")
    sr.add(paths.root, "two", "Two")
    sr.set_default(paths.root, "two")
    assert load_config(paths.root)[1].series == "two"
    sr.rename(paths.root, "two", "deux")
    assert load_config(paths.root)[1].series == "deux"                 # the default followed the rename
    assert sr.registers(paths.root) == ["co_trang_tien_hiep"] or "co_trang_tien_hiep" in sr.registers(paths.root)
    with pytest.raises(SubagentError):
        sr.set_default(paths.root, "missing")


def test_cli_series_commands(project, capsys):
    from subagent.__main__ import main

    _, paths = project
    assert main(["series", "add", "show-b", "--name", "Show B", "--identify-characters"]) == 0
    assert main(["series", "list"]) == 0
    assert "show-b" in capsys.readouterr().out
    assert main(["series", "default", "show-b"]) == 0
    assert load_config(paths.root)[1].series == "show-b"
