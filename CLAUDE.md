# CLAUDE.md — Subtitle Agent

Implementation guide for Claude Code. Read this fully before writing code. When this file and a request conflict, ask before deviating.

## 1. Project overview

A local Python pipeline that translates the burned-in Chinese subtitles (hardsubs) of cartoon series into Vietnamese, adds pinyin, and renders the result back onto the video. It was built on one series (`series-1`) and holds several, each with its own memory, bootstrap, settings and work folder (`data/series/<slug>/`, 5.2a).

Key facts about the source material that drive the design:

- The show is a cartoon built from reused, predrawn character art.
- Voices are AI-generated and consistent per character, but two characters may sound alike.
- Subtitles are hardsubs (pixels), so text must come from OCR.
- Vietnamese pronouns (xưng hô) depend on speaker, listener and their relationship, so speaker/listener attribution is a first-class concern.
- Setting is historical / fantasy (cổ trang, tiên hiệp). Translation uses a classical register and Hán-Việt terms (see 5.11).
- Chinese subtitles are a single line in a fixed position. Resolution is unknown and read at runtime.
- It is unknown whether other text (signs, titles, sound effects) appears in the subtitle area, so the pipeline detects and flags it (see 5.5).
- Episodes are 5–15 minutes, roughly 150–400 subtitle lines each.
- The final video always shows pinyin and Vietnamese together.

Target environment: Windows, NVIDIA GPU. CPU fallback must still work.

Primary goals, in order: translation quality (meaning and correct xưng hô), low cost, low human effort over time.

Two operating modes:

- **Human mode:** the full script (zh / pinyin / vi) is reviewed and edited in the desktop app with a live preview of the new subtitles; the edits flow back into memory.
- **Auto mode:** everything is approved automatically; flagged lines are listed in a report.

## 2. Tech stack

| Area | Choice | Notes |
|---|---|---|
| Language | Python 3.11+, no framework | No LangChain / LlamaIndex / agent frameworks. Plain modules and functions. The desktop app uses PySide6 as a UI toolkit only. |
| Validation | Pydantic v2 | All LLM JSON output and all data models. |
| LLM client | `openai` SDK | Pointed at OpenAI-compatible endpoints via `base_url`. |
| Translator, `utility` role (OCR correction, polyphone fallback, script review, briefings, bootstrap, dreaming) | DeepSeek (`deepseek-chat`) | Model ids in config; verify the current id before first run. |
| Evaluator | Google Gemini (`gemini-3.5-flash-lite`, free tier; was `gemini-3.1-flash-lite`) via its OpenAI-compatible endpoint | Different model family from the translator on purpose. Any OpenAI-compatible provider works; model id in config. |
| Video decode + crop | ffmpeg via `subprocess` | ffmpeg must be on PATH. |
| Change detection, sprite check | OpenCV (`opencv-python-headless`), NumPy | |
| OCR | RapidOCR (PaddleOCR models on ONNX Runtime) | Use `onnxruntime-gpu` (CUDA execution provider) when available, CPU provider otherwise. |
| Audio embeddings | SpeechBrain ECAPA (`speechbrain/spkrec-ecapa-voxceleb`) + torch/torchaudio (CUDA build) | Runs on GPU when available, CPU otherwise. |
| Cast recognition | `transformers` (extra `cast`): OWLv2 `google/owlv2-base-patch16-ensemble` finds characters, DINOv2 `facebook/dinov2-base` describes them | Local, on the GPU when available; models (~0.9 GB) cached in `cache/models/hf`. Tests never load them (5.8b). |
| Video encode | ffmpeg `h264_nvenc` | Falls back to `libx264` if NVENC is unavailable. |
| Pinyin | `pypinyin` + `jieba` | Tone-mark style. |
| Structured memory | SQLite (stdlib `sqlite3`) | |
| Narrative memory | Markdown files | |
| Memory versioning | Git (via `subprocess`) on the memory folder | |
| Desktop app | PySide6 (Qt for Python) | Separate package; the core pipeline never imports it (see 6.1). |
| Video preview | libmpv via `python-mpv` | Renders ASS with libass, the same renderer as ffmpeg's `ass` filter, and applies the mask filter live. Needs `libmpv-2.dll` beside the app on Windows. |
| UI translations | Qt Linguist (`.ts` / `.qm`, `pyside6-lupdate` / `pyside6-lrelease`) | English and Vietnamese. |
| Subtitle output | `pysubs2` (ASS) | |
| Config | YAML (`pyyaml`) + `.env` for secrets (`python-dotenv`) | |
| CLI | `argparse` | |
| Tests / lint | `pytest`, `ruff` | |

Optional, not installed by default: Demucs (vocal separation). Add only if voice-match accuracy on real episodes is poor.

Do not add any dependency outside this table without asking.

## 3. Spec map

The detailed spec (old sections 3.2–6.11) lives in `.claude/rules/`, verbatim and with its section numbers; each file loads automatically when you work on files matching its `paths:`. Read the file before changing its area, and grep `.claude/rules/` for a section number when one is cited (e.g. "5.11"). Old sections 3.1 (pipeline diagram), 7 (design reasons), 10 (implementation order), 11 (project facts) and every measurement moved to `knowledge_vault/` (Vietnamese, for the owner); read them only when a decision's history matters. Each component section lists: responsibility, inputs, outputs, implementation details, config keys, failure handling.

- **Pipeline** ([architecture.md](.claude/rules/architecture.md), 3.2–3.3): stages in order ingest → ocr → events → ocr_fix → audio → voice → cast → pinyin → windows → translate (+ evaluate) → sprite → script_review → review gate; `finish-review` (or auto mode right after the gate) runs memory update → voice / sprite learning → render + deliver → report → cleanup. Each stage reads the previous artifact from `work/<episode_id>/` and is skipped when its input hash in `state.json` is unchanged. Core package `subagent/` (stages, memory, CLI), desktop app `app/` (PySide6, never imported by `subagent/`), prompts in `prompts/`, series data in `data/`.
- **Data models** ([data-models.md](.claude/rules/data-models.md), 4): every artifact is a Pydantic model from `subagent/models.py`, one per JSONL line; the SQLite schema of `data/memory/memory.db` (characters, appearances, glossary, pronoun_pairs, voice_bank, sprite_bank, line_decisions, candidates, memory_log, …) and the Markdown memory (briefings, style rules).
- **Config and series** ([config.md](.claude/rules/config.md), 5.2, 5.2a): every threshold is a key in `config.yaml`, validated by `config.py`; the block lists the code defaults. Several series: `data/series/<slug>/` each (memory, bootstrap, registry, cards, fonts, prompt notes, `series.yaml` overriding config.yaml sections); a path written `data/<x>` in the spec means the active series' folder; active series = `--series`, `$SUBAGENT_SERIES` or `series.default`.
- **OCR** ([ocr.md](.claude/rules/ocr.md), 5.3–5.6, 5.4a): frame sampling with an outline test, RapidOCR in line mode on the calibrated series style (`ocr.preprocess: segment`, symmetric crop), event building (merge, flicker, fragments, non-dialogue flags), OCR correction by the utility model.
- **Voice and cast** ([voice-cast.md](.claude/rules/voice-cast.md), 5.1, 5.7–5.8b, 5.13): the LLM client (cache, cost records, budget, prompt caching rule), ECAPA voice match with statuses fixed / confusable / unknown / too_short / new_voice, automatic `npc_<ep>_<n>` voices, voice learning, OWLv2 + DINOv2 cast recognition and sprite learning, the optional sprite check.
- **Translation** ([translation.md](.claude/rules/translation.md), 5.9–5.14): pinyin, scene windows, translator rules per voice status, register (cổ trang / tiên hiệp, Hán-Việt), evaluator rule checks + rubric and the retry loop, script review (repeats, noise, OCR fixes never applied), review gate and finish review.
- **Memory** ([memory.md](.claude/rules/memory.md), 5.15–5.18): Memory Manager is the only writer (locked entries, evidence rule, conflicts, git commit per episode, rollback as a new commit), character lifecycle, probation for new characters, character updates per episode (5.15c: names, descriptions, aliases, pronoun pairs; locked ones wait in Memory → Character updates), human-edit mining, bootstrap, dreaming.
- **Render, CLI, registry** ([pipeline-cli.md](.claude/rules/pipeline-cli.md), 5.19–5.23): ASS + mask + burn-in (shared builders with the preview), every CLI command, batch, episode registry, output delivery, cleanup.
- **Desktop app** ([app.md](.claude/rules/app.md), 6.1–6.10): jobs as child processes with JSON progress, screens (episodes, review with On screen view and character cards, partial review, preview, bootstrap wizard, memory, dreaming, settings), i18n via `tr()`.
- **Benchmarks** ([benchmarks.md](.claude/rules/benchmarks.md), 6.11–6.11e): audit, speaker and OCR benchmarks, the frozen baseline (its own git repo under `<work>/_baseline/`), the benchmark suite (`bench score|run`, snapshot / chain, `--resume`). Compare experiments with the reference runs recorded there.

## 8. Non-functional requirements

### Cost
- NFR-C1: All non-LLM steps run locally with no paid services.
- NFR-C2: Per-episode LLM spend is tracked per call and reported; the run stops before exceeding `budget.max_cost_per_episode`.
- NFR-C3: Prompts follow the caching layout in 5.1; the report shows the cache-hit share of input tokens.
- NFR-C4: Only failed lines are retranslated, never whole windows.

### Performance
- NFR-P1: The target machine has an NVIDIA GPU. OCR (onnxruntime CUDA provider), voice embeddings (torch CUDA) and encoding (NVENC) use it when `device` is `auto` or `cuda`. Every stage must still run correctly on CPU.
- NFR-P1b: One 5–15 minute episode should process end to end, excluding human review and LLM latency, in a few minutes on the GPU machine. Treat this as a target to measure, not a hard limit.
- NFR-P2: OCR runs only on changed frames.
- NFR-P3: Models (OCR, ECAPA) are loaded once per process.

### Reliability
- NFR-R1: Every stage is resumable. A stage records a hash of its inputs and config section in `work/<episode>/state.json`; it is skipped when the hash matches and its output exists.
- NFR-R2: Artifact writes are atomic (write to a temp file, then rename).
- NFR-R3: Stages are idempotent; rerunning produces the same output given the same inputs and cache.
- NFR-R4: Memory writes are transactional and logged; a failed episode never leaves half-written memory.
- NFR-R5: LLM output that fails validation twice stops the stage with a clear error; it never silently writes partial data.
- NFR-R6: Source videos are never modified, moved or copied by the app or the pipeline.
- NFR-R7: A finished video appears in the output folder only when complete; an existing file is never overwritten without the user's choice (5.22).
- NFR-R8: A missing source video is detected before any stage uses it, and the episode can be relinked without losing results.

### Quality
- NFR-Q1: Glossary terms and locked pronoun pairs are never contradicted in approved output without a flag.
- NFR-Q2: Output subtitles respect `max_line_chars`, `max_lines_per_event` and `max_cps`, or carry a flag.
- NFR-Q3: The report tracks quality metrics per episode (5.20) so trends across episodes are visible.

### Determinism
- NFR-D1: LLM temperature 0 by default.
- NFR-D2: No randomness in local steps.

### Observability
- NFR-O1: `logging` with one logger per module, INFO by default, DEBUG via `--verbose`. Log file per episode in `work/<episode>/run.log`.
- NFR-O2: Every stage logs its start, end, duration and item counts.

### Security
- NFR-S1: API keys only from environment / `.env`; never logged, never written to artifacts or cache keys.
- NFR-S2: `.env`, `data/episodes/`, `data/memory/`, `data/series/*/episodes/`, `data/series/*/memory/`, `work/`, `cache/` are git-ignored.
- NFR-S3: The output folder and working folder may be anywhere on disk, including paths with spaces and Vietnamese or Chinese characters; all path handling must support this.

### Portability
- NFR-PT1: Primary platform is Windows; Linux must also work. Use `pathlib`, no shell-specific syntax; call ffmpeg with argument lists, never `shell=True`.
- NFR-PT2: External binaries required: ffmpeg, ffprobe, git (Git for Windows). Check at startup and print install hints if missing.
- NFR-PT3: Text encoding: open every text file with `encoding="utf-8"` explicitly, and set `PYTHONUTF8=1` in the run instructions. Windows defaults to a legacy code page that corrupts Chinese and Vietnamese text.
- NFR-PT4: SpeechBrain model fetching must use its copy strategy instead of symlinks, because symlinks need admin rights or Developer Mode on Windows.
- NFR-PT5: Install torch from the CUDA wheel index matching the installed driver; document the exact command in `README.md`.

### UX (desktop app)
- NFR-UX1: The UI thread never blocks for more than 100 ms; I/O, model loading and jobs run off the UI thread or in child processes.
- NFR-UX2: A review edit is visible in the live preview within 0.5 s.
- NFR-UX3: No work is lost on a crash or close: review drafts autosave; closing during a job asks whether to cancel it (it can be resumed later).
- NFR-UX4: Every destructive action (rollback, deleting a locked entry, rerun from a stage, finish review) asks for confirmation and states what will change.
- NFR-UX5: The complete review workflow works with the keyboard only.
- NFR-UX6: Chinese characters, pinyin tone marks and Vietnamese diacritics render correctly in every widget, including at Windows high-DPI scaling (bundle Noto Sans and Noto Sans SC and set them as the app font with fallback).
- NFR-UX7: The app opens to a usable Episodes screen in under 3 s; heavy models load only inside jobs.
- NFR-UX8: Errors are shown in plain language with the next action to take, in the selected interface language.

### Maintainability
- NFR-M1: Type hints everywhere; `ruff` clean.
- NFR-M2: Prompts live in `prompts/` as files, not inline strings.
- NFR-M3: Unit tests for every stage with small fixtures; LLM calls mocked in tests via a fake client in `tests/conftest.py`. Tests never download or load ML models (stages that need them are off in the test config or get fakes).

## 9. Rules for Claude Code
- Every change or decision must have a note in `knowledge_vault/decisions/`; do not modify `data/memory/` through the vault.
- Implement in stage order. Each stage must have tests and run on a real short clip before starting the next.
- Never write to memory outside the `memory/manager/` package (the Memory Manager).
- `subagent/` must never import `app/` or PySide6.
- The app never writes pipeline artifacts other than those listed in 6.1; it calls core functions or starts CLI jobs.
- Every user-visible UI string goes through `tr()`; never hardcode interface text.
- Never add a dependency, framework or paid service without asking.
- Never hardcode thresholds, model ids, prices or paths; add them to config.
- Keep prompts in `prompts/`; when changing a prompt, keep the static part stable (caching).
- Use Pydantic models from `models.py` for every artifact; do not pass raw dicts between stages.
- Prefer small pure functions; keep I/O at the stage boundary.
- When a design question is not answered by this file, ask instead of guessing.
- Follow section 12 for every change

## 12. Knowledge vault

`knowledge_vault/` is an Obsidian vault for the human owner: a decision log, not pipeline memory.

- Claude Code is the only writer of `knowledge_vault/`.
- Every change or decision gets a note in `decisions/`: date, decision, reason, measurement if any. Add a line to `changelog/` for each session.
- A fact lives in one place. Thresholds and current behavior stay in `config.yaml` and this file; the vault holds the reasoning and links to them.
- Never modify `data/memory/` through the vault.
- When a section of this file is trimmed, move the history (measurements, dated decisions) to `decisions/` and leave a one-line link.
- After I tell you a branch is merged to main, update the existing diagram files in `knowledge_vault/diagrams/` in place: read the current file, edit it, and overwrite the same file name. Never create a new file or a versioned copy. Create a new file only if no diagram for that subject exists yet, and tell me when you do.
