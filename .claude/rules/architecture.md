---
paths:
  - "subagent/**"
  - "app/**"
  - "tests/**"
  - "prompts/**"
---
### 3.2 Stage order and artifacts

Paths are relative to `subagent/`. Each stage reads the previous stage's artifact from `work/<episode_id>/` and writes its own. A stage is skipped if its output exists and its inputs have not changed (see NFR-Reliability).

| # | Stage | Module | Output artifact |
|---|---|---|---|
| 1 | Frame sampling + change detection | `ocr/ingest.py` | `bands/` (PNG crops of changed frames), `changes.jsonl`, `video.json` |
| 2 | OCR | `ocr/ocr.py` | `ocr_raw.jsonl` |
| 3 | Event building | `ocr/events.py` | `events_raw.jsonl` |
| 4 | OCR correction | `ocr/ocr_fix.py` | `events.jsonl` |
| 5 | Audio extraction | `voice/audio.py` | `audio.wav` |
| 6 | Voice match | `voice/voice.py` | `speakers.jsonl`, `new_voices.json`, `voice_embeddings.npz` |
| 6b | Cast (on screen / talking) | `cast/cast.py` | `cast.jsonl`, `cast_embeddings.npy` |
| 7 | Pinyin | `translation/pinyin_gen.py` | `pinyin.jsonl` |
| 8 | Scene windowing | `translation/windows.py` | `windows.json` |
| 9 | Translate + evaluate loop | `translation/translate.py`, `translation/evaluate.py` | `translations.jsonl`, `evaluations.jsonl`, `memory_prefix.md` |
| 10 | Sprite check | `cast/sprite.py` | updates `translations.jsonl` speaker fields, `sprite.json` |
| 11 | Script review | `translation/script_review.py` | `script_review.jsonl` |
| 12 | Review gate | `review/review.py` | `approved.jsonl` + `edits.jsonl` (auto) or `review_draft.jsonl` + status `awaiting_review` (human) |
| 13 | Human review + finish | `app/views/review.py`, `review/review.py` | `review_draft.jsonl` (autosaved), then `approved.jsonl`, `edits.jsonl` |
| 14 | Memory update | `memory/manager/` | memory DB + briefings, git commit |
| 15 | Voice + sprite learning | `voice/learning.py`, `cast/learning.py` | voice bank + confusable pairs, sprite bank; git commits (5.8a, 5.8b) |
| 16 | Render + deliver | `output/render.py`, `output/delivery.py` | `output.ass`; finished video moved to the output folder |
| 17 | Report | `pipeline/report.py` | `report.md` (`cost.jsonl` is appended by every LLM call) |
| 18 | Cleanup | `output/delivery.py` | temporary files deleted (5.23) |

`state.json` holds the review mode (`human` / `auto`) and each stage's status, input hash, output hash, duration and counts. Stages 14–18 run in `finish-review`, or right after stage 12 in auto mode.

Stages 1–4 and 5–6 are independent and may run in parallel (process-level) once both work correctly in sequence. Implement sequentially first.

### 3.3 Repository layout

```
subagent/              one package per module (3.4); each __init__.py is that module's public API
  __main__.py          CLI entry (argparse): the parser assembled from cli/, main()
  kernel/              shared by every module
    models.py          Pydantic data models of every artifact (section 4)
    errors.py  util.py  textutil.py  progress.py
  settings/
    config.py          load + validate config.yaml / series.yaml into Pydantic models (5.2, 5.2a)
    registers.py       translation styles: prompts/registers/<id>.md, text + pronoun words (5.11)
    schema.py          what the settings form shows: field kinds, help, known sets, which file (6.9)
    yaml_edit.py       set / delete YAML values in place, keeping comments (5.2a)
  infra/               media.py (ffmpeg / ffprobe), device.py (GPU / CPU), joblock.py (job locks)
  llm/client.py        LLM client wrapper, cache, cost records, budget, prompt loading (section 5.1)
  workspace/
    episodes.py        episode registry: add, detect numbers, link, relink (5.21)
    context.py         EpisodeContext: what every stage gets (config, paths, episode, LLM, progress)
    state.py           work/<episode>/state.json
    series.py          several series: add, rename, default, migrate the single-series layout (5.2a)
  memory/
    store.py           SQLite access (read functions are public, write functions are private to manager)
    manager/           Memory Manager (sole writer), one module per responsibility:
      __init__.py      MemoryManager: setup, locking, connections, one write transaction
      apply.py         write rules, Markdown memory, manual edits, conflicts
      episode.py       episode update, lifecycle, line decisions, edit mining, briefings
      candidates.py    probation: candidates, promotion
      updates.py       character updates and the ones waiting for review
      banks.py         voice bank, confusable pairs, sprite bank
      history.py       git commit, history, diff, rollback
      rows.py  results.py  proposals.py   shared helpers (row SQL, result models, proposal merging)
    evidence.py        what an episode's artifacts say for learning: trusted auto-mode lines, line voices
    characters.py      automatic characters from new voices: ids, "unnamed" test, new_voices.json I/O (5.8)
    prefix.py          memory prefix blocks for prompts (5.1 caching rule), reviewer corrections
    briefings.py       Markdown briefing read/write helpers
    briefing_gen.py    per-episode briefing and story compression (utility calls)
    dreaming.py        offline consolidation, rejection memory
    probation.py       new characters on probation: candidate checks, return check (5.15b)
    character_updates.py  per-episode character updates: names, descriptions, aliases, pronoun pairs (5.15c)
  ocr/                 ingest.py, ocr.py, events.py, ocr_fix.py (stages 1-4), subtitle_style.py (5.4a),
                       geometry.py (where the line sits in a band mask)
  voice/               audio.py, voice.py (stages 5-6; also bootstrap clips and centroids), learning.py (5.8a)
  cast/                cast.py, sprite.py (stages 6b, 10), learning.py (sprite learning, 5.8b),
                       card.py (who an id is: name, description, first episode, voice clip, picture; 6.4)
  translation/         pinyin_gen.py, windows.py, translate.py, evaluate.py, script_review.py (stages 7-11)
  bootstrap/seed.py    memory bootstrap (5.17)
  review/              review.py (gate, drafts, finish helpers), partial.py (6.4b)
  output/              render.py (5.19), delivery.py (5.22, 5.23)
  pipeline/
    stages.py          the stage table (3.2): inputs, config sections, outputs; run_stage
    runner.py          Runner (resume logic) and Pipeline: run, batch, finish review, render, calibrate
    report.py          per-episode metrics, report.md, episode status
  bench/               audit.py (6.11), baseline.py (6.11d), benchmark.py (6.11b), ocr_benchmark.py (6.11c),
                       suite.py, bench_run.py (6.11e)
  cli/                 commands, one module per group: episodes.py, memory.py, measure.py, series.py; common.py
app/                   desktop app (PySide6); imports `subagent`, never the reverse
  __main__.py          `python -m app`
  main_window.py       navigation shell, status bar
  services/            the app's only door into the core (3.4):
    core.py            Services: episode status, memory read/write, review draft I/O
    settings.py  episodes.py  review.py  audit.py  memory.py  bootstrap.py
                       per area, what its screens use from the core (lazy re-exports)
  jobs.py              runs CLI commands in QProcess, parses JSON progress lines
  workers.py           QThreadPool helpers for short in-process operations
  preview.py           mpv widget, timeline, mask filter, ASS reload
  messages.py          error codes and statuses → translated text
  shortcuts.py  widgets.py
  views/
    episodes.py  run.py  review.py  memory.py  bootstrap.py  dreaming.py  settings.py
    character_dialog.py  character_browser.py  common.py  settings_form.py  cast_panel.py  audit.py
  i18n/                app_en.ts, app_vi.ts (+ compiled .qm), fill_vi.py (Vietnamese strings)
prompts/               one .md file per prompt, loaded at runtime; registers/<id>.md: translation styles (5.11)
data/series/<slug>/    one folder per series (5.2a); "data/<x>" in this spec means data/series/<slug>/<x>
  series.yaml          overrides of config.yaml sections for this show
  episodes/index.json  episode registry: links to source videos, which stay where they are
  bootstrap/
    cast.md            cast list + synopsis written by the user
    subtitle_style.json  the series' subtitle style, learned once by `calibrate --style` (5.4a)
    voices/<char_id>/*.wav
    sprites/<char_id>/*.png
  character_cards/     card samples the reviewer pinned (6.4)
  fonts/               subtitle font(s) with Vietnamese + pinyin coverage
  prompts/             series notes appended to the general prompts (5.2a)
  memory/              git repo: memory.db, briefings/, style_rules.md, conflicts.json/.md,
                       speaker_corrections.jsonl, dream_proposals.json, dream_state.json, dream_rejections.json,
                       character_updates.json, character_update_rejections.json
app/fonts/             the interface's own font (Noto Sans), independent of any series
work/<slug>/<episode_id>/  per-episode artifacts (not committed); the folder is `paths.work_dir` (a series' own, or
                       <shared work_dir>/<slug>/), may be anywhere
cache/llm/             LLM response cache (not committed)
tests/
config.yaml
.env                   API keys (never committed)
```

### 3.4 Module boundaries

Each package of `subagent/` is a module. Modules work together only through their interfaces; `tests/test_architecture.py` checks every rule below, function-level imports included, and names the file and line of a breach.

- **Public API:** a module's `__init__.py` lists its public names in `__all__` and re-exports them lazily (`_EXPORTS` + `__getattr__`, PEP 562): the submodule is imported the first time a name is used, so importing a package costs nothing and heavy libraries load only where they are used. A name another module needs is added there. A few cohesive submodules are public namespaces, listed in `__all__` (`bench.audit`, `bench.suite`, `workspace.series`, `bootstrap.seed`, `memory.briefings`, `memory.dreaming`, `voice.learning`, `settings.schema`).
- **Imports between modules:** `from subagent.<module> import name` only; never a submodule path (`subagent.voice.voice`), never a `_name`. Inside a module, files import each other directly.
- **Direction:** a module imports only modules on a lower layer, plus `cast → voice` (sprite learning trusts the voice match). When a lower module needs something from a higher one, the higher one passes it in (e.g. `Pipeline(after_finish=[...])`: the CLI adds the baseline copy, so the pipeline does not import `bench`).

  | Layer | Modules |
  |---|---|
  | 0 | kernel |
  | 1 | settings |
  | 2 | infra, llm |
  | 3 | workspace |
  | 4 | memory |
  | 5 | ocr, voice |
  | 6 | cast, translation |
  | 7 | bootstrap, review |
  | 8 | output |
  | 9 | pipeline |
  | 10 | bench |
  | 11 | cli (with `__main__.py`) |

- **Stage modules** are named by path in the stage table (`pipeline/stages.py`, e.g. `"subagent.ocr.ingest"`) and imported when the stage runs, so their models load only then.
- **App:** views, widgets and `app/__main__.py` import from the core only `subagent.kernel` (data types, errors). Everything else comes from `app/services/`: `Services` (`core.py`) and one module per area re-exporting what its screens use.
- **Tests** may import any submodule. Patch a function where its caller looks it up: the package attribute (`monkeypatch.setattr("subagent.infra.extract_clip", …)`) when the caller is in another module, the submodule attribute when it is in the same module; stage `run` functions are patched in their stage module (`"subagent.ocr.ingest.run"`).
- A new package needs a row in the layer table above and in `LAYERS` in `tests/test_architecture.py`.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/map/sơ đồ pipeline.md`.
