# Subtitle Agent

Translates the burned-in Chinese subtitles of cartoon series into Vietnamese, adds pinyin, and renders both back
onto the video. One project holds several series, each with its own memory, settings and work folder.
Design and rules: [CLAUDE.md](CLAUDE.md).

```
video → frames + change detection → OCR → events → OCR fix ─┐
      → audio → voice match → cast (who is on screen) ───────┤
                                  pinyin, scene windows ────┴→ translate ⇄ evaluate → sprite check → script review
      → review (app or auto) → memory update → ASS + mask + burn-in → output folder
```

## Install

### 1. What you need

- Windows 10/11 (Linux also works) and **Python 3.11 or newer** (tested with 3.13).
- An NVIDIA GPU with a recent driver (≥ 570 for CUDA 12.8; `nvidia-smi` shows it). Without a GPU everything
  still runs on the CPU, more slowly: see [CPU only](#cpu-only).
- On `PATH`:
  - **ffmpeg** and **ffprobe**: `winget install Gyan.FFmpeg`
  - **git**: `winget install Git.Git`
- API keys for the LLMs: DeepSeek (translator and utility calls) and Google Gemini (evaluator, free tier).
- Optional, for the live video preview in the review screen: `libmpv-2.dll` in the project folder. Download
  *mpv-dev-x86_64* from the mpv website and copy `libmpv-2.dll` from it. Without it, review still works, just
  without the preview.

### 2. Turn on UTF-8 mode

Always run with UTF-8 mode. Otherwise the legacy Windows code page corrupts Chinese and Vietnamese text.

```powershell
setx PYTHONUTF8 1          # permanent, for new terminals
$env:PYTHONUTF8 = "1"      # this terminal
```

### 3. Create a virtual environment and install the packages

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` installs everything at the tested versions, including PyTorch for CUDA 12.8 (from the
PyTorch wheel index) and the CUDA / cuDNN libraries GPU OCR needs. It is a large download (several GB).

An older driver that does not support CUDA 12.8: in `requirements.txt`, change `cu128` in the index URL and in
the two torch versions to the CUDA version your driver supports (for example `cu126`:
`https://download.pytorch.org/whl/cu126`, `torch==2.11.0+cu126`), then run the install again.

### 4. Add the API keys

Copy `.env.example` to `.env` and fill in the keys. You can also do this in the app later, under Settings → API
keys. The key names are the `api_key_env` values in `config.yaml` (`llm.providers`):

```
DEEPSEEK_API_KEY=...
GEMINI_API_KEY=...
```

Keys are read only from `.env` or the environment. They are never written to logs or artifacts.

### 5. Check the setup

```powershell
python -m subagent check
```

This reports missing binaries (with install hints), the device in use (GPU / CPU), fonts, the output folder and
API keys. Before the first run, also:

- check the model ids in `config.yaml` (`llm.providers.*.model`);
- fill `llm.prices`, so the cost report and the per-episode budget work;
- set the output folder: `output.folder` in `config.yaml`, or in the app under Settings → Files.

The two cast-recognition models (about 0.9 GB) and the voice model download into `cache/models/` the first time
an episode uses them.

### CPU only

`requirements.txt` works on a machine without an NVIDIA GPU too: torch and ONNX Runtime fall back to the CPU.
Set `device: cpu` in `config.yaml` (or Settings) so nothing tries CUDA first. OCR then takes about 1 s per
changed frame.

To use the smaller CPU builds instead (several GB less on disk), replace them after installing:

```powershell
pip uninstall -y onnxruntime-gpu
pip install onnxruntime==1.30.0
pip install --force-reinstall --no-deps torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
```

## Run

Every time, in a new terminal, from the project folder:

```powershell
$env:PYTHONUTF8 = "1"                 # unless set permanently with setx
.\.venv\Scripts\Activate.ps1          # Linux: source .venv/bin/activate
```

### The desktop app

```powershell
python -m app
```

Everything can be done from the app: add episodes, run them, review, bootstrap, memory, settings. A new series
starts at **New series…** in the series picker (top of the sidebar). It then opens the Bootstrap screen. See
[First episode of a series](#first-episode-of-a-series) for the steps.

### The command line

Translating one episode:

```powershell
python -m subagent add "D:\show\第1集.mp4"     # register the video (linked, never copied)
python -m subagent run ep001                   # human mode: stops when the draft is ready for review
python -m app                                  # review it: Review screen, then Finish review
# or, without the app, after editing <work>\ep001\review_draft.jsonl:
python -m subagent finish-review ep001         # memory update, render; the video lands in the output folder
```

`python -m subagent run ep001 --mode auto` approves everything automatically and lists flagged lines in
`<work>/ep001/report.md`. A stopped run resumes where it left off: run the same command again. All commands
are listed in [Commands](#commands).

## Series

Each series (show) has its own folder `data/series/<slug>/`: memory (its own git repo), bootstrap inputs, the
episode registry, character cards, the subtitle font (`fonts/`, Noto Sans included under the SIL Open Font
License), prompt notes for that show, and `series.yaml`, which overrides any section of the shared
`config.yaml` for that show (subtitle band, OCR, cast, voice, work folder, …).

```powershell
python -m subagent series list                      # * marks the default series
python -m subagent series add my-show --name "My Show" --pronouns ta ngươi [--work-dir "E:\My Show\work"]
python -m subagent series add other-show --name "Other" --identify-characters
python -m subagent series default my-show           # the series the app and the CLI use
python -m subagent series rename series-1 my-first-show
python -m subagent run ep001 --series my-show       # any command, for another series than the default
```

In the app, the series picker at the top of the sidebar switches series; **New series…** creates one and opens
its Bootstrap screen. Without its own `paths.work_dir`, a series works in `<work_dir>/<slug>/`.

Each series uses a **translation style** (`show.genre_register`): a file `prompts/registers/<id>.md` with the
translator's instructions for that kind of show and the pronoun words the rule check looks for. Cổ trang /
tiên hiệp is built in; create another in the app (New series… → **New style…**) or by adding a file in the same
format. `series add --register <id>` picks one.

Each series also chooses how **pronouns** (xưng hô) are decided. With `--identify-characters` (the app's
**Identify characters** box) the program finds who speaks to whom from voices and pictures and uses the pronoun
matrix per pair; this needs voice clips in Bootstrap. With `--pronouns SELF ADDRESS` (box unchecked, the default
pronoun pair filled in) there is no character identification: the voice, cast and sprite stages are skipped and
every line uses that one pair. Change it later in Settings → Advanced → show (`character_identification`,
`self_term`, `address_term`).

## First episode of a series

Paths below are in the series folder `data/series/<slug>/`.

1. **Add videos** (they are linked, never copied): `python -m subagent add "D:\show\第1集.mp4"` or a folder
   (`--recursive` for subfolders). Numbers are detected from file names and you confirm them.
2. **Calibrate** the subtitle band once: `python -m subagent calibrate ep001`, look at
   `<work>/ep001/calibration/*.png`, and set `video.subtitle_band` (or drag the rectangle in the app:
   Bootstrap → Calibrate, which saves it to the series' `series.yaml`). Then learn the subtitle style:
   `python -m subagent calibrate ep001 --style`.
3. **Bootstrap memory**: write `bootstrap/cast.md` (see `data/series/series-1/bootstrap/cast.example.md`), put
   3–5 voice clips per character in `bootstrap/voices/<char_id>/` and optional sprite crops in
   `bootstrap/sprites/<char_id>/` (only with character identification on; the app's Bootstrap wizard captures both from the video), then
   `python -m subagent bootstrap`, review `bootstrap/seed_draft.json`, and
   `python -m subagent bootstrap --approve`.
4. **Set the output folder** in `config.yaml` (`output.folder`) or Settings → Files.
5. **Run**: `python -m subagent run ep001` (human mode stops at review) or `--mode auto`.
6. **Review** in the app (`python -m app`) → Review, or edit `<work>/ep001/review_draft.jsonl`, then
   `python -m subagent finish-review ep001`. Memory is updated and the video lands in the output folder as
   `<source name>_vi.mp4`.
7. **Next episodes**, in episode order (memory builds up episode by episode): `python -m subagent run ep002`, or
   several at once: `python -m subagent batch --pending`. Between episodes: `python -m subagent dream` and
   review the proposals (app → Dreaming).

Tune thresholds after the first episode: `<work>/ep001/report.md` shows voice-match status shares,
first-pass evaluator rate, flag counts, non-dialogue suspects and cost.

## Commands

Every command accepts `--series SLUG`, `--progress json` (one JSON object per line: `stage`, `status`,
`done`, `total`, `cost`, `message`, `error_code`) and `--verbose`. `python -m subagent <command> --help`
lists a command's options.

```
# episodes
python -m subagent add PATH... [--recursive] [--number N] [--yes]
python -m subagent relink EPISODE PATH [--keep | --rerun]
python -m subagent calibrate EPISODE [--style]
python -m subagent run EPISODE [--mode auto|human] [--from STAGE] [--force STAGE] [--rerun] [--no-cache] [--on-exists ...]
python -m subagent batch [EPISODE...] [--pending] [--mode auto|human] [--rerun] [--max-total-cost USD] [--keep-going | --stop-on-error]
python -m subagent partial-review EPISODE     # mid-review: learn from approved lines, re-check the rest
python -m subagent finish-review EPISODE [--on-exists overwrite|keep-both|fail]
python -m subagent render EPISODE [--on-exists overwrite|keep-both|fail]
python -m subagent clean EPISODE
python -m subagent status [EPISODE] [--json]
python -m subagent check

# memory
python -m subagent bootstrap [--approve] [--voices CHAR_ID...]
python -m subagent dream [--auto-apply]
python -m subagent voices learn|evaluate
python -m subagent sprites learn

# series
python -m subagent series list|add|default|rename|migrate ...

# measuring
python -m subagent audit sample|report|benchmark|ocr|remap-key [EPISODE...]
python -m subagent baseline freeze|complete NAME [EPISODE...]
python -m subagent bench score|run [EPISODE...] [--mode snapshot|chain] [--from STAGE] [--label L] [--no-cache] [--resume RUN]
```

Stages, in order: `ingest ocr events ocr_fix audio voice cast pinyin windows translate sprite script_review
review`. Stages resume: a finished stage is skipped while its inputs, prompts and config are unchanged.

## Desktop app

`python -m app`. Screens: Episodes (add, run, resume, rerun, render, relink, cleanup, live run panel), Review
(live preview, character cards, On screen view, keyboard shortcuts), Memory (edit, history, diff, rollback,
character updates), Bootstrap wizard, Dreaming, Audit, Settings (Advanced: every setting as a form with search; changes are saved in
place, so the comments in config.yaml and series.yaml stay). Interface language: English or Tiếng Việt
(Settings → Language).

After changing UI strings, refresh the translations:

```powershell
pyside6-lupdate (Get-ChildItem app\*.py, app\views\*.py) -ts app\i18n\app_vi.ts -ts app\i18n\app_en.ts
python app\i18n\fill_vi.py      # add new strings to the VI table in that file first; compiles the .qm files
```

## Development

`requirements.txt` already includes pytest and ruff.

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
