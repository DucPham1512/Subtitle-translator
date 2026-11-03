---
name: graph-refactor
description: Find what is worth refactoring in this repo from the graphify knowledge graph (graphify-out/graph.json), turn the verified findings into a ranked plan, and after the owner picks a target, refactor it step by step with ruff and pytest green after each step. Use this whenever the user wants to refactor, clean up, restructure, untangle or simplify this codebase and the question is WHAT to change or WHERE to start, for "use the graph / graphify to refactor", "what should I refactor", "split this big file or class", "this view is too big", "find dead code", "reduce coupling", "code health", or after /graphify when they ask what the graph says about the code. For the mechanics of one already chosen move (extract method, rename) the refractor skill is enough; this skill picks the targets, proves them with graph evidence and keeps the project's rules intact.
---

# Graph-driven refactoring

The graph tells you **what** to refactor and **why**; the `refractor` skill tells you **how** to do each move; this
repo's rules decide what you may not touch. Refactoring here means the behaviour stays the same: the test suite
passes before and after, unchanged except for import paths.

Work in two halves with a stop in between: **plan** (read-only), then wait for the owner to pick a target, then
**refactor** that one target. The owner decides what gets changed, because a refactor touches code they maintain
and the graph only sees structure, not intent.

## 1. Make sure the graph is current

```bash
python .claude/skills/graph-refactor/scripts/refactor_targets.py --json <scratchpad>/targets.json
```

The first line of its output says whether the graph is stale (Python files changed since the commit it was built
from). If it is, refresh it before trusting anything: `graphify update .` re-reads code only (AST, no LLM, free).
If there is no `graphify-out/graph.json`, ask the owner to run `/graphify` first. `.graphifyignore` already keeps
docs, the vault, skills and media out, so the graph is code plus the files the code reads at run time.

## 2. Read the leads, then verify every one

The script ranks seven kinds of leads. Each is a lead, not a verdict: the graph comes from static analysis and some
edges are INFERRED (name matching). Read the code behind a lead before it goes into a plan.

| Section | What it suggests | Known false positives in this repo |
|---|---|---|
| 1. App files that drive the core | A view reaching many core modules holds core logic that belongs behind `app/services/` or in the core | The names come through `app/services/*` lazy re-exports, which is correct; the import rules are `tests/test_architecture.py`'s job. The signal is *how much* core work a view does, not a broken rule |
| 1. Coupling between modules | A heavy pair may have a missing abstraction | Edges to `kernel` / `settings` are left out on purpose: every module uses the foundation |
| 2. Files that do several jobs | Symbols spread over many communities: a split candidate | `kernel/models.py` and `kernel/util.py` span communities by design (the spec keeps every artifact model in `models.py`) |
| 3. Large classes, long functions | God class / long method | Qt view classes are big partly because of slots; count real responsibilities, not methods |
| 4. Hubs | Blast radius of a change, not a target | Being used everywhere is their job |
| 5. Import cycles | Tangled modules | Lazy `__getattr__` exports and `TYPE_CHECKING` imports never run at import time |
| 6. Unreferenced symbols | Dead code | Already filtered: names written anywhere else, decorated functions (validators, properties). Still grep, and check `__all__`, `_lazy("…")` strings in `pipeline/stages.py`, CLI tables |
| 7. Same name in several files | Possible duplication | A shared name is not shared code: compare the bodies (signatures and return types first) before calling it duplication |

Tools for checking a lead: `graphify explain "<symbol>"` (neighbours), `graphify affected "<symbol>" --depth 2`
(what breaks if it changes), `graphify path "<A>" "<B>"`, `git log --oneline --since=3.months -- <file>` (how
often it changes: churn makes a refactor pay off), Read and grep. Drop leads that do not survive; say which you
dropped and why, so the owner can see the filter worked.

## 3. Write the plan and stop

Rank verified targets by: how much the problem costs (size, mixed jobs, duplication) × how often the code changes,
weighed against risk (blast radius, test cover). Five targets at most; fewer good ones beat a long list.

Use this shape:

```markdown
# Refactor plan (graph built at <commit>)

| # | Target | Evidence (graph) | Problem (verified in code) | Proposed moves | Blast radius | Risk |
|---|---|---|---|---|---|---|
| 1 | `<file>` `<Class or function>` | <methods / communities / lines / edges> | <what is wrong, in code terms> | <named moves: what goes where> | <affected files; tests that cover it> | low / medium / high |

Dropped leads: …
Rules this plan touches: … (or none)
```

Name concrete moves (Extract Class, Move Function, Inline, Remove Dead Code; see the `refractor` skill's
`code-smells.md` and `techniques.md`) and, for a split, which methods or functions go where, grouped by the
communities the graph found. Then ask the owner which target to do (AskUserQuestion), and stop. Do not edit
anything before they pick: they may know a reason the graph cannot see.

If the owner names the target up front ("refactor X, go ahead"), the pick is made: verify X, show a short plan for
it, and continue with step 4 without asking again.

## 4. Refactor the chosen target

1. **Branch.** If on `main`, create `refactor/<short-slug>` first.
2. **Baseline.** `.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q -p no:warnings` must pass before you
   change anything (in a git worktree without its own `.venv`, use the main checkout's
   `/home/pham-duc/Subtitle-translator/.venv/bin/python`, run from the worktree root so the worktree's code is
   tested). If the baseline fails, stop and report; never refactor on red.
3. **Small steps.** One move at a time; after each, run ruff and the tests for the touched area; run the full suite
   and `tests/test_architecture.py` at the end. A test that needs a change other than an import path means
   behaviour changed: stop and ask.
4. **Keep the repo's rules** (CLAUDE.md §9 and `.claude/rules/architecture.md` 3.4):
   - modules import each other only through their package API (`from subagent.<module> import name`) and only
     downwards; a moved public name stays in (or is added to) that package's `__all__` / lazy `_EXPORTS`;
   - `subagent/` never imports `app/` or PySide6; app views import from the core only `subagent.kernel`, the rest
     through `app/services/`;
   - only `memory/manager/` writes memory; artifacts stay Pydantic models from `kernel/models.py`;
   - user-visible UI strings stay inside `tr()`; thresholds, model ids and paths stay in config;
   - match the surrounding code's naming, comment density and idiom; the repo does not use `ruff format`, so do
     not reformat untouched lines.
   If the refactor would contradict the spec in `.claude/rules/` (for example moving a file the repository layout
   names), ask before doing it, and update the layout in `architecture.md` when a file moves.
5. **Measure.** Refresh the graph (`graphify update .`; add `--force` when code was deleted, because update refuses
   to shrink the graph) and rerun the script. Report the target's numbers before → after (methods, communities,
   lines, unreferenced count…).
6. **Record.** CLAUDE.md §12: a decision note in `knowledge_vault/decisions/<dd-mm-yyyy>/<yyyy-mm-dd> <title>.md`
   (Vietnamese, same frontmatter as the other notes: date, type: decision, status, tags; sections Quyết định,
   Lý do, Kết quả with the before/after numbers) and a line in `knowledge_vault/changelog/<yyyy-mm-dd>.md` linking
   it. Do not commit unless the owner asks.

## 5. Report

Finish with: what changed (files, moves), the test and lint results with counts, the graph numbers before → after,
anything you found but left alone, and the next target from the plan if there is one.
