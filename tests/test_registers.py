"""Translation styles (registers): shared files in prompts/registers/, their pronoun words, the series creator."""

from __future__ import annotations

import pytest
import yaml

from subagent import series as sr
from subagent.config import load_config
from subagent.kernel.errors import SubagentError
from subagent.registers import list_registers, load_register, save_register, split_terms


def test_a_new_style_is_saved_listed_and_never_overwritten(project):
    _, paths = project
    save_register(paths.root, "hien_dai", "Hiện đại", "## Register: hiện đại\n\nModern city life.\n",
                  split_terms("tôi, bạn; anh\nem, tôi"))
    style = load_register(paths.root, "hien_dai")
    assert (style.name, style.pronoun_terms) == ("Hiện đại", ["tôi", "bạn", "anh", "em"])
    assert style.body.startswith("## Register: hiện đại")
    assert {r.id for r in list_registers(paths.root)} == {"co_trang_tien_hiep", "hien_dai"}
    with pytest.raises(SubagentError):
        save_register(paths.root, "hien_dai", "again", "x", [])
    with pytest.raises(SubagentError):
        save_register(paths.root, "Hiện đại", "bad id", "x", [])
    with pytest.raises(SubagentError):
        save_register(paths.root, "empty", "no text", "  ", [])


def test_a_series_takes_its_styles_text_and_pronoun_words(project):
    config, paths = project
    assert "ta" in config.translate.pronoun_terms                 # cổ trang: words from its style file
    save_register(paths.root, "hien_dai", "Hiện đại", "## Register: hiện đại\n", ["tôi", "bạn"])
    sr.add(paths.root, "modern", "Modern", "hien_dai")
    cfg, _ = load_config(paths.root, "modern")
    assert cfg.show.genre_register == "hien_dai" and cfg.translate.pronoun_terms == ["tôi", "bạn"]
    folder = paths.root / "data" / "series" / "modern"
    own = yaml.safe_load((folder / "series.yaml").read_text(encoding="utf-8"))
    own["translate"] = {"pronoun_terms": ["mình", "cậu"]}            # an explicit list still overrides
    (folder / "series.yaml").write_text(yaml.safe_dump(own, allow_unicode=True), encoding="utf-8")
    assert load_config(paths.root, "modern")[0].translate.pronoun_terms == ["mình", "cậu"]
    with pytest.raises(SubagentError):
        sr.add(paths.root, "other", "Other", "no_such_style")


def test_the_translator_prompt_uses_the_series_style(project):
    from subagent.pipeline import _prompt_hash
    from subagent.stages.translate import translator_static

    config, paths = project
    save_register(paths.root, "hien_dai", "Hiện đại", "## Register: hiện đại\n\nModern city life.\n", ["tôi"])
    sr.add(paths.root, "modern", "Modern", "hien_dai")
    cfg, sp = load_config(paths.root, "modern")
    prompt = (paths.prompts / "translator_system.md").read_text(encoding="utf-8")
    text = translator_static(prompt, "hien_dai", cfg, load_register(paths.root, "hien_dai").body)
    assert "Modern city life." in text and "cổ trang" not in text
    assert _prompt_hash(sp, "translator_system", cfg) != _prompt_hash(paths, "translator_system", config)
