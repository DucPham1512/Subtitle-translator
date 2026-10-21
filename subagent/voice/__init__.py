"""Voice (5.7-5.8a): audio extraction, voice match and new voices, bootstrap centroids, voice learning."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.voice import learning
    from subagent.voice.learning import Clip, embed_clips, episode_samples, learn_voices
    from subagent.voice.voice import (
        all_similarities,
        compute_centroids,
        get_embedder,
        l2_normalize,
        match_events,
        pair_similarities,
        voice_clips,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "Clip": ("subagent.voice.learning", "Clip"),
    "all_similarities": ("subagent.voice.voice", "all_similarities"),
    "compute_centroids": ("subagent.voice.voice", "compute_centroids"),
    "embed_clips": ("subagent.voice.learning", "embed_clips"),
    "episode_samples": ("subagent.voice.learning", "episode_samples"),
    "get_embedder": ("subagent.voice.voice", "get_embedder"),
    "l2_normalize": ("subagent.voice.voice", "l2_normalize"),
    "learn_voices": ("subagent.voice.learning", "learn_voices"),
    "match_events": ("subagent.voice.voice", "match_events"),
    "pair_similarities": ("subagent.voice.voice", "pair_similarities"),
    "voice_clips": ("subagent.voice.voice", "voice_clips"),
}

__all__ = ["Clip", "all_similarities", "compute_centroids", "embed_clips", "episode_samples", "get_embedder", "l2_normalize", "learn_voices", "learning", "match_events", "pair_similarities", "voice_clips"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
