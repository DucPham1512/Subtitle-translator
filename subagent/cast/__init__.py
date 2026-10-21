"""Cast (5.8b, 5.13): who is on screen and talking, the sprite check, sprite learning, character cards."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.cast.card import card_info, card_media, pin_card, shown_talking_box
    from subagent.cast.cast import NOT_A_CHARACTER, build_bank, frame_time_ms, load_frame, match
    from subagent.cast.learning import apply_review_edits, frame_embedder, learn_sprites, plan
    from subagent.cast.sprite import save_template

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "NOT_A_CHARACTER": ("subagent.cast.cast", "NOT_A_CHARACTER"),
    "apply_review_edits": ("subagent.cast.learning", "apply_review_edits"),
    "build_bank": ("subagent.cast.cast", "build_bank"),
    "card_info": ("subagent.cast.card", "card_info"),
    "card_media": ("subagent.cast.card", "card_media"),
    "frame_embedder": ("subagent.cast.learning", "frame_embedder"),
    "frame_time_ms": ("subagent.cast.cast", "frame_time_ms"),
    "learn_sprites": ("subagent.cast.learning", "learn_sprites"),
    "load_frame": ("subagent.cast.cast", "load_frame"),
    "match": ("subagent.cast.cast", "match"),
    "pin_card": ("subagent.cast.card", "pin_card"),
    "plan": ("subagent.cast.learning", "plan"),
    "save_template": ("subagent.cast.sprite", "save_template"),
    "shown_talking_box": ("subagent.cast.card", "shown_talking_box"),
}

__all__ = ["NOT_A_CHARACTER", "apply_review_edits", "build_bank", "card_info", "card_media", "frame_embedder", "frame_time_ms", "learn_sprites", "load_frame", "match", "pin_card", "plan", "save_template", "shown_talking_box"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
