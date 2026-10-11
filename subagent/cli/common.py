"""Helpers shared by the CLI commands."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from subagent.config import Config, Paths
from subagent.errors import SubagentError

ON_EXISTS_CHOICES = ["overwrite", "keep-both", "fail"]

log = logging.getLogger("subagent")


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()

def _ask(prompt: str, choices: dict[str, str]) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return choices[answer]

def _resolve_on_exists(config: Config, paths: Paths, ep_ref: str, arg: str | None) -> str:
    """CLI: --on-exists wins; otherwise config; `ask` prompts on a terminal and fails when non-interactive."""
    from subagent.delivery import target_path
    from subagent.episodes import Registry

    choice = (arg or config.output.on_exists).replace("-", "_")
    if choice != "ask":
        return choice
    if not _interactive():
        return "fail"
    try:
        target = target_path(config, Path(Registry(paths).resolve(ep_ref).source_path))
    except SubagentError:
        return "fail"   # the pipeline reports the missing output folder
    if not target.exists():
        return "fail"
    return _ask(f"{target} already exists. [o]verwrite, [k]eep both, [c]ancel? ",
                {"o": "overwrite", "k": "keep_both", "c": "fail"})

def _output_exists(config, paths, ep_ref: str) -> bool:
    from subagent.delivery import target_path
    from subagent.episodes import Registry

    try:
        return target_path(config, Path(Registry(paths).resolve(ep_ref).source_path)).exists()
    except SubagentError:
        return False
