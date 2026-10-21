"""Editing YAML values in place: comments, order and other values stay as they are."""

from __future__ import annotations

import pytest
import yaml

from subagent.settings.yaml_edit import delete_key, set_mapping, set_value

TEXT = """# shared settings
video:
  sample_fps: 4            # measured on ep001
  subtitle_band: {top: 0.8, bottom: 0.9}
cast:
  queries:                 # what OCR-free detection looks for
  - a cartoon character
  - a dog
  match_similarity: 0.7
llm:
  prices:
    deepseek-chat: {input: 0.27, output: 1.1}
    gemini-3.1-flash-lite:
      input: 0
      output: 0
"""


def test_a_value_changes_on_its_line_and_the_comment_stays():
    out = set_value(TEXT, "video.sample_fps", 5)
    assert "  sample_fps: 5            # measured on ep001\n" in out
    assert out.replace("sample_fps: 5", "sample_fps: 4") == TEXT


def test_lists_and_nested_flow_mappings():
    out = set_value(TEXT, "cast.queries", ["a cartoon character", "a cat"])
    assert "  queries: [a cartoon character, a cat]                 # what OCR-free" in out
    assert yaml.safe_load(out)["cast"]["match_similarity"] == 0.7     # the next key is untouched
    out = set_value(TEXT, "video.subtitle_band.left", 0.1)             # a key inside a flow mapping
    assert yaml.safe_load(out)["video"]["subtitle_band"] == {"top": 0.8, "bottom": 0.9, "left": 0.1}


def test_new_keys_and_sections_are_added_at_the_end_of_their_block():
    out = set_value(TEXT, "cast.add_similarity", 0.85)
    data = yaml.safe_load(out)
    assert data["cast"]["add_similarity"] == 0.85 and list(data) == ["video", "cast", "llm"]
    out = set_value(TEXT, "memory.probation_window", 3)
    assert yaml.safe_load(out)["memory"] == {"probation_window": 3} and out.startswith("# shared settings")


def test_keys_with_dots_delete_and_mapping_replace():
    out = set_value(TEXT, ["llm", "prices", "gemini-3.1-flash-lite", "input"], 0.1)
    assert yaml.safe_load(out)["llm"]["prices"]["gemini-3.1-flash-lite"] == {"input": 0.1, "output": 0}
    out = delete_key(TEXT, ["llm", "prices", "gemini-3.1-flash-lite"])
    assert list(yaml.safe_load(out)["llm"]["prices"]) == ["deepseek-chat"]
    out = set_mapping(TEXT, ["llm", "prices"], {"deepseek-chat": {"input": 0.3, "output": 1.1},
                                                "new-model": {"input": 1, "output": 2}})
    assert yaml.safe_load(out)["llm"]["prices"] == {"deepseek-chat": {"input": 0.3, "output": 1.1},
                                                    "new-model": {"input": 1, "output": 2}}
    assert "# what OCR-free detection looks for" in out
    assert delete_key(TEXT, "no.such.key") == TEXT


def test_an_edit_in_a_broken_file_fails_instead_of_writing():
    with pytest.raises(yaml.YAMLError):
        set_value("a: 1\nb: [1, 2\n", "a", 3)                          # broken elsewhere: never written
