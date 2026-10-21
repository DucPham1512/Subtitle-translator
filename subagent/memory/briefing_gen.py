"""One utility call per episode that drafts the episode briefing and updates the story summary."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from subagent.kernel.models import ReviewedLine
from subagent.llm import build_messages, load_prompt
from subagent.memory import briefings as bf
from subagent.memory.prefix import characters_block
from subagent.memory.store import MemoryStore
from subagent.settings.config import Config, Paths


class CharacterFate(BaseModel):
    id: str = Field(description="character id")
    fate: Literal["dies", "leaves", "returns"]
    evidence: str = Field(default="", description="the line that states it (Chinese), with its event id if known")


class BriefingResponse(BaseModel):
    summary_sentence: str = Field(description="One sentence summarizing the episode, in Vietnamese")
    characters_introduced: list[str] = Field(default_factory=list, description="character ids new in this episode")
    episode_markdown: str = Field(description="Episode briefing in Markdown")
    story_so_far: str = Field(description="Updated rolling summary of the whole series so far")
    character_fates: list[CharacterFate] = Field(
        default_factory=list, description="only fates the script states explicitly; usually empty")


class StoryResponse(BaseModel):
    story_so_far: str


def script_text(lines: list[ReviewedLine]) -> str:
    rows = []
    for line in lines:
        who = f"{line.speaker or '?'} → {line.listener or '?'}"
        if line.line_type != "dialogue":
            who = f"[{line.line_type}]"
        rows.append(f"{who}: {line.zh} | {line.vi}")
    return "\n".join(rows)


def generate_briefing(paths: Paths, config: Config, store: MemoryStore, episode_id: str,
                      approved: list[ReviewedLine], llm: object) -> BriefingResponse:
    cap = config.memory.story_so_far_max_words
    static = load_prompt(paths, "briefing_system").replace("{{story_max_words}}", str(cap))
    index = [e.model_dump() for e in bf.read_index(paths.memory)]
    variable = (
        f"Episode: {episode_id}\n\n"
        f"Episode index (episode order):\n{json.dumps(index, ensure_ascii=False, indent=1)}\n\n"
        f"Current story so far:\n{bf.read_story(paths.memory).strip() or '(empty)'}\n\n"
        f"Approved script of {episode_id} (speaker → listener: Chinese | Vietnamese):\n{script_text(approved)}\n"
    )
    messages = build_messages(static, characters_block(store), variable)
    brief: BriefingResponse = llm.call("utility", messages, BriefingResponse, task="briefing")  # type: ignore[attr-defined]
    if bf.word_count(brief.story_so_far) > cap:
        brief.story_so_far = compress_story(paths, brief.story_so_far, cap, llm)
    return brief


def compress_story(paths: Paths, story: str, cap: int, llm: object) -> str:
    static = load_prompt(paths, "story_compress_system").replace("{{story_max_words}}", str(cap))
    messages = build_messages(static, "", story)
    result: StoryResponse = llm.call("utility", messages, StoryResponse, task="briefing")  # type: ignore[attr-defined]
    return result.story_so_far
