---
paths:
  - "subagent/stages/render.py"
  - "subagent/pipeline.py"
  - "subagent/__main__.py"
  - "subagent/episodes.py"
  - "subagent/delivery.py"
  - "subagent/state.py"
---
### 5.19 Output renderer (`stages/render.py`)

- **ASS:** `pysubs2` with two styles, both always rendered: `Pinyin` (smaller, top line) and `Vi` (larger, below), positioned inside the original subtitle band. Set `PlayResX/PlayResY` to the video resolution and scale font sizes by `height / 1080`.
  - Each approved line produces one pinyin event and one Vietnamese event with the same timing.
  - Pinyin is longer than the Chinese line: if it exceeds the band width, shrink it down to `pinyin_min_scale`, then wrap to a second line.
  - Lines with `line_type` other than `dialogue` use a separate `Sign` style (italic) and no pinyin wrapping rules.
- **Mask + burn-in:** one ffmpeg pass:
  - `mask: blur` → crop the band, `boxblur`, overlay it back; `mask: box` → `drawbox` filled with a solid color.
  - then `ass=output.ass:fontsdir=fonts`.
  - Encoder: `h264_nvenc -cq {quality}` when `encoder=auto` and NVENC is available (check once with `ffmpeg -encoders`), otherwise `libx264 -crf {quality}`. Audio `-c:a copy` when the codec is MP4-compatible (AAC, MP3, Opus), otherwise re-encode to AAC.
  - Output container is always MP4. ffmpeg writes to `work/<episode>/render.tmp.mp4`; delivery (5.22) moves it to the output folder.
- **Shared builders:** `build_ass(lines, config, width, height)` and `build_mask_filter(config, width, height)` are the only places that define subtitle styling and masking. The app's live preview uses the same functions, so the preview matches the final render.
- **Windows path handling:** the `ass=` filter argument breaks on drive letters and backslashes. Run ffmpeg with `cwd=work/<episode>/` and pass relative paths (`ass=output.ass:fontsdir=fonts`, with fonts copied or linked into the work dir). Never build filter strings from absolute Windows paths.
- The font must cover Vietnamese diacritics and pinyin tone marks; check at startup that the font file exists.

### 5.20 Pipeline and CLI (`pipeline.py`, `__main__.py`)

Commands:

```
python -m subagent add PATH... [--recursive] [--number N] [--yes]   # register video files and/or folders
python -m subagent relink EPISODE PATH [--keep|--rerun]   # point an episode at its moved video
python -m subagent calibrate EPISODE [--style]   # sample frames with the subtitle band drawn / learn the series' subtitle style (5.4a); one-time setup
python -m subagent bootstrap                 # generate seed draft
python -m subagent bootstrap --approve       # write the (edited) seed draft to memory
python -m subagent bootstrap --voices CHAR_ID...   # recompute only these characters' voices
python -m subagent run EPISODE [--mode auto|human] [--from STAGE] [--force STAGE] [--rerun] [--no-cache] [--on-exists ...]
python -m subagent batch [EPISODE...] [--pending] [--mode auto|human] [--on-exists ...] [--keep-going|--stop-on-error] [--max-total-cost USD] [--rerun] [--no-cache]
python -m subagent finish-review EPISODE [--on-exists ...]
python -m subagent render EPISODE [--on-exists overwrite|keep-both|fail]
python -m subagent clean EPISODE             # delete temporary files now
python -m subagent dream [--auto-apply]
python -m subagent voices learn|evaluate      # rebuild the voice bank now / measure voice-match accuracy (5.8a)
python -m subagent sprites learn             # cast stage where missing + sprite learning, finished episodes (5.8b)
python -m subagent series list|add|default|rename|migrate ...   # several series (5.2a)
python -m subagent partial-review EPISODE    # mid-review: learn from approved lines, re-check the remaining (6.4b)
python -m subagent audit sample|report|benchmark|ocr|remap-key [EPISODE...] [--redraw] [--label NAME] [--no-cache] [--existing] [--archive DIR]   # 6.11, 6.11b, 6.11c
python -m subagent baseline freeze NAME [EPISODE...]   # copy finished reviews into a fixed baseline (6.11d)
python -m subagent baseline complete NAME   # add files an older baseline lacks, and the current OCR answer key (6.11d)
python -m subagent bench score [EPISODE...] [--system DIR] [--baseline NAME] [--label L]   # benchmark suite (6.11e)
python -m subagent bench run [EPISODE...] [--mode snapshot|chain] [--from STAGE] [--label L] [--no-cache] [--resume RUN]
python -m subagent status [EPISODE] [--json] # stage completion, cost (total and per agent), flag counts
python -m subagent check                     # binaries, fonts, output folder, API keys, missing prices, device
```

- Every command accepts `--series SLUG` (the series to work on, 5.2a; default `series.default`; the app's jobs pass it as `$SUBAGENT_SERIES`), `--progress json` and `--verbose`. With `--progress json`: one JSON object per line on stdout (`stage`, `status`, `done`, `total`, `cost`, `message`, `error_code`). The desktop app uses this.
- `run` in human mode stops at `awaiting_review`; the app (or `finish-review`) continues through memory update and render.
- `run --rerun` (`pipeline.RERUN_FROM`): every stage from `ocr_fix` (the first that reads memory) runs again with today's memory, also for a `done` or `awaiting_review` episode; the stages before it rerun only if their video or config changed (their output would be identical otherwise). In human mode the review draft is rebuilt (a review in progress is lost); memory and the delivered video change only when the new run is finished. Unchanged LLM calls come from the cache.
- **Batch** (`Pipeline.run_batch`, `batch`): several episodes in episode-number order in one process (models load once; each episode's memory update happens before the next starts). Episodes already `done` or `awaiting_review` are skipped unless `--rerun` (each episode then runs as `run --rerun`); `--pending` takes every other registered episode. On a failure, auto mode stops (later episodes build on earlier memory) and human mode carries on; `--keep-going` / `--stop-on-error` override. `--max-total-cost` stops before starting another episode once the batch has spent that much (the per-episode budget still applies). Progress: `batch` events (`progress` with "epXXX (i/N)" before each episode, `info` for skips/failures, `done` with a summary); the command exits 1 when an episode failed. In auto mode with `on_exists: ask`, the CLI asks once for all episodes whose output exists (non-interactive: `fail`).
- A lock file `work/<episode>/.lock` prevents two jobs on the same episode.
- `report.md` per episode: stage timings, cost (total vs budget, unpriced models, cache-hit share, by role, by agent), voice-match status shares, evaluator pass rate on first attempt, retry rate, flag counts by type, flagged lines, sprite trigger/resolve counts, human edit rate. Stage counts (e.g. script review removals by source, new voices) are in `state.json` and the run log.
- Before a run, models without a price in `llm.prices` are reported (`error_code: price_missing`).

### 5.21 Episode registry (`episodes.py`)

- **Responsibility:** add episode videos, assign episode numbers, and keep track of where each video lives.
- **Adding videos** (the app offers all of these, and the CLI accepts files and folders):
  - one file, several files, or a folder (videos directly inside it; an "include subfolders" option scans recursively);
  - drag and drop of files and folders onto the Episodes screen.
  - Only files with an extension in `episodes.video_extensions` are considered; each is checked with ffprobe and rejected with a reason if it has no video stream.
- **Episode numbers:**
  - Detected from the file name with `episodes.number_patterns`, tried in order (Chinese `第3集`, `EP03`, `E03`, then any number). The first match wins.
  - The user always confirms: the app shows a table of file → detected number (editable, empty when nothing was detected) before anything is registered. The CLI prints the same table and asks for confirmation, or takes `--number N` for a single file.
  - Numbers must be unique. A file whose fingerprint matches an already registered episode is reported as a duplicate and skipped.
  - Episode id = `ep` + number zero-padded to 3 digits. Episodes sort by number everywhere, including `briefings/INDEX.md`.
- **Order check:** memory builds up episode by episode, so running an episode while a lower-numbered episode is not `done` shows a warning (allowed, not blocked). The briefing and story summary always use episode order, not processing order.
- **Link only:** the registry stores the absolute path, size, modification time and fingerprint. The video is never copied or modified.
- **Missing or changed source:**
  - Before any stage that reads the video (ingest, audio, sprite check, render, preview), the path is checked. If the file is gone, the status becomes `missing` and the app offers **Relink** (pick the new location).
  - On relink, the fingerprint is compared. A mismatch shows a warning that it may be a different file and that existing results may not line up; the user chooses to keep the results or rerun from the start.
- **Registry file:** `data/episodes/index.json`, written atomically.

### 5.22 Output delivery (`delivery.py`)

- **Output folder:** a single default folder set in Settings (`output.folder`). It is required: rendering is blocked with a clear message until it is set. On startup and before each render, check that it exists and is writable.
- **What is saved there:** only the finished video. Scripts, subtitle files, reports and logs stay in the working folder.
- **File name:** `<source file stem><output.name_suffix>.mp4`, e.g. `ep03.mkv` → `ep03_vi.mp4`.
- **Name conflict:** checked before rendering starts, so no render is wasted, and again just before the move.
  - App (`on_exists: ask`): dialog with Overwrite, Keep both, Cancel. Keep both appends ` (2)`, ` (3)`, … before the extension.
  - CLI: `--on-exists overwrite|keep-both|fail`; defaults to `fail` when there is no interactive terminal.
- **Move:** the finished `render.tmp.mp4` is moved into the output folder only after ffmpeg exits successfully. When the output folder is on another drive, copy to a temp name in the output folder, then rename, so a half-written video never appears under the final name.
- The final path is stored in the registry (`output_path`). The app's "Open output folder" selects that file in Explorer.

### 5.23 Cleanup (`delivery.py`)

- **When:** automatically when an episode becomes `done` (review finished and video delivered), if `cleanup.auto` is true. Also available as `python -m subagent clean EPISODE` and from the app.
- **Deleted (temporary):** `bands/`, `audio.wav`, `preview.ass`, `calibration/`, `render.tmp.mp4`, `sprite_frames/`, `cast_frames/`, `ocr_samples/`, `ocr_crops/`, the `fonts` copy in the work folder.
- **Kept:** everything else, notably `events.jsonl`, `speakers.jsonl`, `new_voices.json`, `voice_embeddings.npz`, `cast.jsonl`, `cast_embeddings.npy`, `pinyin.jsonl`, `translations.jsonl`, `evaluations.jsonl`, `script_review.jsonl`, `partial_review.jsonl`, `audit_sample.jsonl`, `audit_marks.jsonl`, `review_draft.jsonl`, `approved.jsonl`, `edits.jsonl`, `output.ass`, `report.md`, `cost.jsonl`, `run.log`, `state.json`, `video.json`.
- `state.json` marks the cleaned stages as `purged`, so resume logic knows their outputs were removed on purpose. Re-rendering needs only the kept files and the source video. Rerunning an earlier stage (e.g. OCR) regenerates its temporary files as normal.
