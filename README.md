# Subtitle Agent

Translates the burned-in Chinese subtitles of one cartoon series into Vietnamese, adds pinyin, and renders
both back onto the video. Design and rules: [CLAUDE.md](CLAUDE.md).

```
video → frames + change detection → OCR → events → OCR fix ─┐
      → audio → voice match ────────────────────────────────┤
                                  pinyin, scene windows ────┴→ translate ⇄ evaluate → sprite check
      → review (app or auto) → memory update → ASS + mask + burn-in → output folder
```

## Requirements

- Windows 10/11 (Linux also works), Python 3.11+, an NVIDIA GPU (CPU works too, slower).
- On `PATH`: **ffmpeg** and **ffprobe** (`winget install Gyan.FFmpeg`), **git** (`winget install Git.Git`).
- Optional, for the live preview: `libmpv-2.dll` next to the project (download *mpv-dev-x86_64* from the
  mpv website, copy `libmpv-2.dll` into this folder). Without it, review still works without a preview.

## Setup

Always run with UTF-8 mode, or Chinese and Vietnamese text gets corrupted by the legacy Windows code page:

```powershell
$env:PYTHONUTF8 = "1"          # or set it permanently: setx PYTHONUTF8 1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[app,ocr,dev]"
```

Voice match needs PyTorch with CUDA. Install torch from the CUDA wheel index that matches your driver
(`nvidia-smi` shows the driver's CUDA version; drivers ≥ 570 support CUDA 12.8), **then** SpeechBrain:

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install "speechbrain>=1.0"
```

(For CPU only: `pip install torch torchaudio` from the default index.)

Characters on screen (the cast stage) needs `transformers` on top of torch; the two models (about 0.9 GB)
download into `cache/models/hf` on first use:

```powershell
pip install -e ".[cast]"
```

To fill the sprite bank from episodes you already finished: `python -m subagent sprites learn`.

GPU OCR: `onnxruntime-gpu` 1.30 needs the CUDA 13 runtime and cuDNN 9 DLLs. Either install the CUDA 13
toolkit + cuDNN 9 system-wide, or let pip fetch them: `pip install "onnxruntime-gpu[cuda,cudnn]"` (the app calls
`onnxruntime.preload_dlls()`). Without them OCR runs on the CPU (about 1 s per changed frame), and
`python -m subagent check` reports the device in use.

API keys go in `.env` (copy `.env.example`), or in the app under Settings → API keys:

```
DEEPSEEK_API_KEY=...
QWEN_API_KEY=...
```

Check everything with `python -m subagent check`. Verify the model ids in `config.yaml`
(`llm.providers.*.model`) and fill `llm.prices` before the first run, so cost reports and the budget work.

A subtitle font covering Vietnamese diacritics and pinyin tone marks must be in `fonts/`
(Noto Sans is included, under the SIL Open Font License, `fonts/OFL.txt`).

## First episode

1. **Add videos** (they are linked, never copied): `python -m subagent add "D:\show\第1集.mp4"` or a folder
   (`--recursive` for subfolders). Numbers are detected from file names and you confirm them.
2. **Calibrate** the subtitle band once: `python -m subagent calibrate ep001`, look at
   `work/ep001/calibration/*.png`, adjust `video.subtitle_band` in `config.yaml` (or drag the rectangle in the
   app: Bootstrap → Calibrate).
3. **Bootstrap memory**: write `data/bootstrap/cast.md` (see `data/bootstrap/cast.example.md`), put 3–5 voice
   clips per character in `data/bootstrap/voices/<char_id>/` and optional sprite crops in
   `data/bootstrap/sprites/<char_id>/` (the app's Bootstrap wizard captures both from the video), then
   `python -m subagent bootstrap`, review `data/bootstrap/seed_draft.json`, and
   `python -m subagent bootstrap --approve`.
4. **Set the output folder** in `config.yaml` (`output.folder`) or Settings → Files.
5. **Run**: `python -m subagent run ep001` (human mode stops at review) or `--mode auto`.
6. **Review** in the app (`python -m app`) → Review, or edit `work/ep001/review_draft.jsonl`, then
   `python -m subagent finish-review ep001`. Memory is updated and the video lands in the output folder as
   `<source name>_vi.mp4`.
7. Between episodes: `python -m subagent dream` and review the proposals (app → Dreaming).

Tune thresholds in `config.yaml` after the first episode: `work/ep001/report.md` shows voice-match status
shares, first-pass evaluator rate, flag counts, non-dialogue suspects and cost.

## Commands

```
python -m subagent add PATH... [--recursive] [--number N] [--yes]
python -m subagent relink EPISODE PATH [--keep | --rerun]
python -m subagent calibrate EPISODE
python -m subagent bootstrap [--approve] [--voices CHAR_ID...]
python -m subagent run EPISODE [--mode auto|human] [--from STAGE] [--force STAGE] [--no-cache] [--on-exists ...]
python -m subagent finish-review EPISODE [--on-exists overwrite|keep-both|fail]
python -m subagent render EPISODE [--on-exists overwrite|keep-both|fail]
python -m subagent clean EPISODE
python -m subagent dream [--auto-apply]
python -m subagent status [EPISODE] [--json]
python -m subagent check
```

Every command accepts `--progress json` (one JSON object per line: `stage`, `status`, `done`, `total`, `cost`,
`message`, `error_code`) and `--verbose`. Stages: `ingest ocr events ocr_fix audio voice pinyin windows
translate sprite review`. Stages resume: a finished stage is skipped while its inputs and config are unchanged.

## Desktop app

`python -m app`. Screens: Episodes (add, run, resume, rerun, render, relink, cleanup, live run panel), Review
(flagged lines first, live preview, keyboard shortcuts), Memory (edit, history, diff, rollback), Bootstrap
wizard, Dreaming, Settings. Interface language: English or Tiếng Việt (Settings → Language).

After changing UI strings, refresh the translations:

```powershell
pyside6-lupdate (Get-ChildItem app\*.py, app\views\*.py) -ts app\i18n\app_vi.ts -ts app\i18n\app_en.ts
python app\i18n\fill_vi.py      # add new strings to the VI table in that file first; compiles the .qm files
```

## Development

```powershell
pytest          # unit + pipeline + offscreen app tests; LLM calls use the fake client in tests/conftest.py
ruff check .
```

## Implementation notes

Decisions where CLAUDE.md left room, recorded here for review:

- `pronoun_pairs.context` is `NOT NULL DEFAULT ''` (the default pair is `''`): SQLite would otherwise allow
  duplicate primary keys with `NULL` context.
- `memory_log` has an extra `evidence_count` column, used by the "more evidence wins" conflict rule.
- History diffs compare the `memory.db` snapshots of a commit and its parent (plus the Markdown diff), so they
  stay correct after a rollback removed later `memory_log` rows.
- Conflicts are kept in `conflicts.json` (machine-readable) and rendered to `conflicts.md`.
- The bootstrap seed is human-reviewed, so bootstrap writes count as human for the lock rule. A dreaming
  proposal on a locked entry that the user explicitly accepts in the app is applied as a human edit.
- The translate stage retries only failed lines; an identical retry prompt is served from the LLM disk cache.
- Rule checks: a pronoun term that conflicts with the matrix fails the line only when none of the pair's
  terms is used; otherwise it is a warning (avoids retries on third-person mentions).
- `ReviewedLine` has a `line_type` field and `SubtitleEvent` has `flags`/`notes`/box geometry, needed by the
  review screen and non-dialogue detection.
- Extra config keys: `video.empty_text_ratio`, `non_dialogue.enabled`, `voice.model`, `pinyin.*`,
  `translate.pronoun_terms`, `evaluate.*`, `memory.dream_max_lines`, render layout metrics, `llm.timeout_s`.
