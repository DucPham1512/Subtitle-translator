---
paths:
  - "subagent/ocr/ingest.py"
  - "subagent/ocr/ocr.py"
  - "subagent/ocr/events.py"
  - "subagent/ocr/ocr_fix.py"
  - "subagent/ocr/subtitle_style.py"
  - "prompts/ocr_fix_system.md"
---
### 5.3 Frame sampling + change detection (`ocr/ingest.py`)

- **Responsibility:** find the moments when the subtitle band changes, without OCR-ing every frame.
- **Input:** episode video path.
- **Output:** `bands/<frame_ms>.png` for each changed frame, `changes.jsonl` with `{t_ms, kind: "text"|"empty"}`.
- **Details:**
  - Run ffmpeg with `-vf fps={sample_fps},crop=...` computed from `subtitle_band` fractions and the probed resolution (`ffprobe`). Pipe raw gray frames (`-pix_fmt gray -f rawvideo`) into NumPy; do not write every frame to disk.
  - Binarize each band with `text_threshold`. Compare to the previous binarized band; a change is `mean(abs diff) > change_threshold`.
  - A band holds a subtitle only if its bright-pixel share is ≥ `empty_text_ratio` and, with `subtitle_detection: outline`, its share of bright pixels within `outline_reach_px` of a dark (≤ `outline_dark_threshold`) pixel is ≥ `min_outlined_ratio`. Burned-in subtitles are outlined; snow, sky or white clothes are not. Bright bands without outlined text are skipped (counted as `no_subtitle_frames`).
  - A band without a subtitle after one with text is `kind="empty"` (subtitle ended).
  - Save only changed, non-empty bands as PNG. Probed video facts go to `video.json`.
- **Failure handling:** missing ffmpeg or unreadable video → fail fast with a clear message.
- **Calibration:** `python -m subagent calibrate EPISODE` saves a few sample frames with the configured band drawn as a rectangle to `work/<episode>/calibration/`, so the user can adjust `video.subtitle_band` once. The position is fixed across episodes, so this is a one-time step.

### 5.4 OCR (`ocr/ocr.py`)

- **Responsibility:** read Chinese text from saved bands.
- **Output:** `ocr_raw.jsonl` with `{t_ms, text, confidence, boxes}`.
- **Details:**
  - One RapidOCR engine instance, reused.
  - Subtitles are a single line: sort detected boxes left to right and join them without separators.
  - Keep each reading's bounding box (height, vertical center, horizontal center); the event builder uses them for non-dialogue detection.
  - More than one text row in the band is unexpected for dialogue: keep the text, record `multi_row=true`.
  - Strip characters outside CJK, CJK punctuation and digits.
  - Keep results below `ocr.min_confidence` but mark them; do not drop them.
  - **Engine:** RapidOCR's detection resize is configurable (`det_limit_type`, `det_limit_side_len`, `use_cls`). Its default scales the band's short side to 736 px (about 15x for a 48 px band): slow (about 0.5–1.3 s per band on the CPU) but measured better than a 960 px cap (6.11c). The log names the execution provider really used: RapidOCR silently falls back to the CPU (onnxruntime-gpu 1.30 is built for CUDA 13, PyTorch here ships CUDA 12.8).
  - **Pre-processing** (`preprocess: mask`): `subtitle_mask` keeps bright strokes (≥ `mask_bright`) whose edge is mostly (≥ `mask_min_outline`) within `mask_reach_px` of a dark (≤ `mask_dark`) pixel and that are at most glyph-sized (`mask_max_height` / `mask_max_width` band heights); scenery and props (sky, a white cooler with black writing) are dropped. `mask_image` chooses what OCR reads: `mask` (black text on white), `original` (the band's pixels) or `isolated` (band pixels inside the mask widened by `isolate_grow_px`, black elsewhere); enlarged by `mask_scale`, padded by `mask_pad`.
  - **Line recognition** (`recognize: line`, with `preprocess: mask`): the mask's components are grouped left to right while the gap is ≤ `box_max_gap` band heights; the group with the most ink is the subtitle line (none when lower than `line_min_height`). Only that crop goes to the recognition model (no detection); the reading is mapped back to band coordinates.
  - **Symmetric crop** (`symmetric_crop`, line mode; user decision 2026-10-03; code default off, the project's `config.yaml` sets it on with tolerance 0.75): subtitles are centred on the frame, so the side of the line farther from the frame's centre column is trimmed to the other side's length plus `symmetric_crop_tolerance` line heights (the line's own height; a letter segmentation missed at the short end is not answered by cutting a real one off the long end). A line that does not reach across the centre is read as nothing. Strays the line grouping joins at one end (a fish head beside the first letter, a flower after the last) fall outside the crop. The OCR crop, the review screen's "OCR read" image and the calibration preview all use the trimmed crop. Measured in 6.11c.
  - **Box filter** (`box_filter`, detect mode): keeps the box with the most characters and the boxes beside it at least `box_min_height` as tall and within `box_max_gap` line heights; drops prop labels and numbers next to the line.
  - `save_crops` (with any pre-processing): each reading's OCR input is saved as `ocr_crops/<t_ms>.png`, drawn at its position on a band-sized grey canvas so it lines up with the original band; the review screen shows it (6.4). Temporary (5.23).
  - `sample_images` > 0 saves that many evenly spaced before/after images (`ocr_samples/<t_ms>.png` + `.txt` with the reading) for inspection; temporary (5.23).
  - All options default to today's behaviour; which to switch on is decided by the OCR benchmark (6.11c).
  - **Resolution** (`video.band_frames` > 1, 5.3): ingest keeps the frames that still show the same subtitle; the saved band is their per-pixel median (static text sharpens, compression noise and moving background average out) and `bands/<t>.stable.png` marks pixels that changed by at most `video.stable_range`. Plain upscaling is not used: the recognizer resizes every crop to 48 px tall.

### 5.4a Generic subtitle segmentation (`ocr/subtitle_style.py`, `ocr.preprocess: segment`)

- **Calibration, once per series** (user decision 2026-10-03; `python -m subagent calibrate EPISODE --style`, or the bootstrap wizard's Calibrate step, 6.6): bands sampled across one episode (`video.calibrate_fps`, at most `calibrate_max_bands`). Candidate regions come from MSER and from connected components at a few grey levels (Otsu and fixed steps; threshold-based), in both polarities; the stroke-width transform (edge-based: Canny edges paired across each stroke along the gradient, rays capped at a third of the band height) measures their stroke widths. Text-like regions (letter-sized, stroke widths consistent, unchanged between consecutive samples) are kept. The polarity whose regions are consistently set off from their surroundings wins (an outline, itself a constant-width stroke, has fill on one side and background on the other); with an outline, only outlined regions are learned from. Saved to `data/bootstrap/subtitle_style.json` (series data, not `config.yaml`, which would lose its comments): polarity, fill grey range (two thirds of the way from the outline to the fill, leaving room for compression), outline level, stroke width and letter height as shares of the band height. A preview (band above, segmentation below) goes to `work/<episode>/calibration/style.png`. With `preprocess: segment` the OCR stage's input hash includes the style's values (not its date or region count), so a new calibration re-reads the subtitles of every episode run afterwards; other pre-processing never reads it.
- **Segmentation, every band:** fill-range components (threshold) whose median SWT stroke width is within `seg_stroke_tolerance` of the series', at most `seg_max_height` / `seg_max_width` letter heights, ringed by the outline for at least `seg_outline_share` of their surroundings when the style has one, and at least `seg_min_stable` still when ingest saved a stability map. Region growing then adds neighbouring components on the same rows that pass every test but the stroke width (letters at a line's ends still widen the line). The result feeds line grouping, cropping and recognition like the show-tuned mask.
- **Outline level:** a quarter of the way from the outline's typical grey towards the fill.
- **In use** (user decision 2026-10-03): the project's `config.yaml` sets `ocr.preprocess: segment`, `recognize: line`, `mask_image: original`, `mask_scale: 1.0`, `symmetric_crop: true` (tolerance 0.75) and `video.band_frames: 5` (code defaults stay off, since segmentation needs a calibrated style). `python -m subagent check` reports a missing style; tests reset these keys (`tests/conftest.py`). Generality can only be measured on a second series with its own answer key.

### 5.5 Event building (`ocr/events.py`)

- **Responsibility:** turn per-frame OCR results into subtitle events with start and end times.
- **Details:**
  - Consecutive readings whose normalized text is within `merge_max_edit_distance` belong to one event; the most frequent reading wins as `zh_raw`.
  - `start_ms` = first frame of the event; `end_ms` = next change or empty frame.
  - Flicker: back-to-back groups with matching text merge, and a single misread sample between two matching groups (A, X, A) is dropped.
  - Fragments: an event on screen for ≤ `ocr.fragment_max_samples` sampled frames (counted by time on screen, not by OCR readings) is folded into a touching neighbour whose text is ≥ `fragment_merge_similarity` similar or contains it; the neighbour keeps its text and takes the time. Fragments with no such neighbour stay, flagged `ocr_fragment`.
  - Events with mean confidence < `ocr.min_confidence` get `ocr_low_conf`.
  - Assign ids `<episode_id>:<index>`.
- **Non-dialogue detection** (`non_dialogue.enabled`; it is unknown whether signs, titles or sound-effect text appear in the band):
  - Compute the median box height and center over all events in the episode; those represent normal dialogue.
  - Flag `non_dialogue_suspect` when an event's box height or center deviates beyond `non_dialogue.box_height_tolerance` / `box_center_tolerance`, when `multi_row=true`, or when duration > `non_dialogue.max_duration_ms`.
  - Suspect events are not dropped. They skip voice match and go to the translator marked as suspect (5.11).
  - The report shows the suspect count, so the thresholds can be tightened or the check turned off once the show's behavior is known.

### 5.6 OCR correction (`ocr/ocr_fix.py`)

- **Responsibility:** fix OCR character errors (similar-looking characters) using context and the glossary.
- **Details:**
  - Batches of `ocr_fix.batch_size` events, sent to the `utility` role with the glossary (zh terms only) in the memory prefix.
  - The model returns only the lines it changes, with a reason.
  - Code rejects any change over `max_char_changes` characters, and adds flag `ocr_uncertain` instead.
  - Output `events.jsonl` with `zh` and `ocr_fixed`.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/decisions/đo lường - OCR.md`.
