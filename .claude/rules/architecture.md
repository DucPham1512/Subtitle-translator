---
paths:
  - "subagent/**"
  - "app/**"
  - "tests/**"
  - "prompts/**"
---
### 3.2 Stage order and artifacts

Each stage reads the previous stage's artifact from `work/<episode_id>/` and writes its own. A stage is skipped if its output exists and its inputs have not changed (see NFR-Reliability).

| # | Stage | Module | Output artifact |
|---|---|---|---|
| 1 | Frame sampling + change detection | `stages/ingest.py` | `bands/` (PNG crops of changed frames), `changes.jsonl`, `video.json` |
| 2 | OCR | `stages/ocr.py` | `ocr_raw.jsonl` |
| 3 | Event building | `stages/events.py` | `events_raw.jsonl` |
| 4 | OCR correction | `stages/ocr_fix.py` | `events.jsonl` |
| 5 | Audio extraction | `stages/audio.py` | `audio.wav` |
| 6 | Voice match | `stages/voice.py` | `speakers.jsonl`, `new_voices.json`, `voice_embeddings.npz` |
| 6b | Cast (on screen / talking) | `stages/cast.py` | `cast.jsonl`, `cast_embeddings.npy` |
| 7 | Pinyin | `stages/pinyin_gen.py` | `pinyin.jsonl` |
| 8 | Scene windowing | `stages/windows.py` | `windows.json` |
| 9 | Translate + evaluate loop | `stages/translate.py`, `stages/evaluate.py` | `translations.jsonl`, `evaluations.jsonl`, `memory_prefix.md` |
| 10 | Sprite check | `stages/sprite.py` | updates `translations.jsonl` speaker fields, `sprite.json` |
| 11 | Script review | `stages/script_review.py` | `script_review.jsonl` |
| 12 | Review gate | `stages/review.py` | `approved.jsonl` + `edits.jsonl` (auto) or `review_draft.jsonl` + status `awaiting_review` (human) |
| 13 | Human review + finish | `app/views/review.py`, `stages/review.py` | `review_draft.jsonl` (autosaved), then `approved.jsonl`, `edits.jsonl` |
| 14 | Memory update | `memory/manager.py` | memory DB + briefings, git commit |
| 15 | Voice + sprite learning | `memory/voice_learning.py`, `memory/sprite_learning.py` | voice bank + confusable pairs, sprite bank; git commits (5.8a, 5.8b) |
| 16 | Render + deliver | `stages/render.py`, `delivery.py` | `output.ass`; finished video moved to the output folder |
| 17 | Report | `pipeline.py` | `report.md` (`cost.jsonl` is appended by every LLM call) |
| 18 | Cleanup | `delivery.py` | temporary files deleted (5.23) |

`state.json` holds the review mode (`human` / `auto`) and each stage's status, input hash, output hash, duration and counts. Stages 14–18 run in `finish-review`, or right after stage 12 in auto mode.

Stages 1–4 and 5–6 are independent and may run in parallel (process-level) once both work correctly in sequence. Implement sequentially first.

### 3.3 Repository layout

```
subagent/
  __main__.py          CLI entry (argparse)
  config.py            load + validate config.yaml into Pydantic models
  models.py            shared Pydantic data models (section 4)
  llm.py               LLM client wrapper, cost records (section 5.1)
  pipeline.py          stage orchestration, resume logic, report, episode status
  episodes.py          episode registry: add, detect numbers, link, relink (5.21)
  delivery.py          output naming, conflict handling, move to output folder, cleanup (5.22, 5.23)
  characters.py        automatic characters from new voices: ids, "unnamed" test, new_voices.json I/O (5.8)
  context.py  state.py  progress.py  joblock.py  media.py  device.py  textutil.py  util.py  errors.py
  ocr_benchmark.py     raw OCR scored against the corrected Chinese of reviewed episodes (6.11c)
  baseline.py          fixed copy of finished reviews for benchmarks (6.11d)
  suite.py             benchmark suite: five benchmarks scored against a baseline (6.11e)
  bench_run.py         sandbox re-run of the baseline's episodes for the suite: snapshot / chain memory (6.11e)
  character_card.py    who an id is: name, description, first episode, voice clip, picture (6.4)
  subtitle_style.py    generic subtitle segmentation: stroke-width transform, series style calibration (5.4a)
  stages/
    ingest.py  ocr.py  events.py  ocr_fix.py  audio.py  voice.py
    pinyin_gen.py  windows.py  translate.py  evaluate.py  sprite.py
    cast.py  script_review.py  review.py  render.py
  memory/
    store.py           SQLite access (read functions are public, write functions are private to manager)
    manager.py         Memory Manager (sole writer)
    prefix.py          memory prefix blocks for prompts (5.1 caching rule), reviewer corrections
    briefings.py       Markdown briefing read/write helpers
    briefing_gen.py    per-episode briefing and story compression (utility calls)
    bootstrap.py       memory bootstrap
    dreaming.py        offline consolidation, rejection memory
    probation.py       new characters on probation: candidate checks, return check (5.15b)
    voice_learning.py  voice bank learned from reviewed lines, auto-mode gate, evaluation (5.8a)
    sprite_learning.py sprite bank learned from talking sprites and trusted speakers (5.8b)
app/                   desktop app (PySide6); imports `subagent`, never the reverse
  __main__.py          `python -m app`
  main_window.py       navigation shell, status bar
  services.py          thin adapter over core: episode status, memory read/write, review draft I/O
  jobs.py              runs CLI commands in QProcess, parses JSON progress lines
  workers.py           QThreadPool helpers for short in-process operations
  preview.py           mpv widget, timeline, mask filter, ASS reload
  messages.py          error codes and statuses → translated text
  shortcuts.py  widgets.py
  views/
    episodes.py  run.py  review.py  memory.py  bootstrap.py  dreaming.py  settings.py
    character_dialog.py  character_browser.py  common.py
  i18n/                app_en.ts, app_vi.ts (+ compiled .qm), fill_vi.py (Vietnamese strings)
prompts/               one .md file per prompt, loaded at runtime
data/
  episodes/index.json  episode registry: links to source videos, which stay where they are
  bootstrap/
    cast.md            cast list + synopsis written by the user
    subtitle_style.json  the series' subtitle style, learned once by `calibrate --style` (5.4a)
    voices/<char_id>/*.wav
    sprites/<char_id>/*.png
  memory/              git repo: memory.db, briefings/, style_rules.md, conflicts.json/.md,
                       speaker_corrections.jsonl, dream_proposals.json, dream_state.json, dream_rejections.json
fonts/                 subtitle font(s) with Vietnamese + pinyin coverage
work/<episode_id>/     per-episode artifacts (not committed); the folder is `paths.work_dir`, may be anywhere
cache/llm/             LLM response cache (not committed)
tests/
config.yaml
.env                   API keys (never committed)
```

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/map/sơ đồ pipeline.md`.
