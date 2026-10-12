---
paths:
  - "subagent/config.py"
  - "config.yaml"
  - "tests/conftest.py"
  - "subagent/series.py"
  - "data/series/**"
---
### 5.2 Config (`config.py`, `config.yaml`)

Pydantic-validated. Every threshold in this document is a config key; no magic numbers in code. Example:

```yaml
show:
  name: "<show name>"
  genre_register: "co_trang_tien_hiep"  # translation style: prompts/registers/<id>.md (text + pronoun words)
  character_identification: true      # off: no speakers, one default pronoun pair for every line (5.11a)
  self_term: ""                       # the default pair (required when identification is off), e.g. ta
  address_term: ""                    # ...e.g. ngươi
device: auto                          # auto | cuda | cpu
video:
  sample_fps: 4
  subtitle_band: {top: 0.80, bottom: 0.97, left: 0.05, right: 0.95}   # fractions of frame, set via `calibrate`
  text_threshold: 200                 # grayscale threshold for subtitle glyphs
  change_threshold: 0.02              # fraction of band pixels changed
  empty_text_ratio: 0.002             # fewer bright pixels than this fraction: empty band
  subtitle_detection: outline         # outline: bright text with a dark outline | bright: any bright pixels
  outline_dark_threshold: 60          # grayscale at or below this is an outline pixel
  outline_reach_px: 2                 # a bright pixel this close to a dark one is outlined
  min_outlined_ratio: 0.006           # fewer outlined bright pixels: no subtitle (snow, sky, white clothes)
  band_frames: 1                      # fuse up to this many frames of the same subtitle per band (median); 1 = off
  stable_range: 12                    # grey change at most this across those frames: a stable pixel
  calibrate_fps: 2.0                  # style calibration sampling (5.4a)
  calibrate_max_bands: 400
ocr:
  min_confidence: 0.6
  merge_max_edit_distance: 1
  fragment_max_samples: 1             # events on screen for this many sampled frames or fewer are fragments
  fragment_merge_similarity: 0.6      # fold a fragment into a touching neighbour this similar (or containing it)
  det_limit_type: min                 # RapidOCR detection resize (its defaults: min 736, i.e. a 48 px band ~15x)
  det_limit_side_len: 736
  use_cls: true                       # text-direction classifier
  preprocess: none                    # none | mask (show-tuned, 5.4) | segment (calibrated series style, 5.4a)
  mask_bright: 200                    # subtitle fill at or above this grey level...
  mask_dark: 60                       # ...outline at or below this
  mask_reach_px: 2
  mask_min_outline: 0.6               # share of a stroke's edge that must be outlined
  mask_max_height: 1.0                # stroke components at most this tall (band heights)...
  mask_max_width: 1.6                 # ...and this wide; larger bright areas are scenery
  mask_min_area: 4
  mask_min_mean: 0                    # mask: mean grey of a stroke at least this (0 = off)
  mask_max_stroke: 0.0                # mask: widest stroke inside, share of the band height (0 = off)
  mask_scale: 2.0                     # enlarge what OCR reads
  mask_pad: 8
  recognize: detect                   # detect | line: crop the masked line, recognition model only
  line_min_height: 0.4                # a component group lower than this share of the band is specks
  mask_image: mask                    # mask (black on white) | original (band pixels) | isolated
  isolate_grow_px: 3                  # also the crop margin in line mode
  line_crop_vertical: false
  symmetric_crop: false               # line mode: trim the crop side farther from the frame's centre (5.4)
  symmetric_crop_tolerance: 0.5       # ...leaving this much difference, in line heights
  seg_stroke_tolerance: 0.6           # segment: stroke width within this share of the series' width
  seg_outline_share: 0.5              # segment: share of the ring around a component that is outline
  seg_max_height: 1.3                 # segment: at most this many letter heights tall...
  seg_max_width: 2.0                  # ...and wide (larger pieces are background)
  seg_min_stable: 0.6                 # segment: share of a component that stayed still (with band_frames > 1)
  box_filter: false                   # drop OCR boxes beside the line (detect mode)
  box_min_height: 0.7
  box_max_gap: 1.5                    # in line heights; also the component gap in line mode
  sample_images: 0                    # before/after band images saved to ocr_samples/ (temporary)
  save_crops: true                    # what OCR read, per reading, to ocr_crops/ for the review screen (temporary)
non_dialogue:
  enabled: true
  box_height_tolerance: 0.25          # relative deviation from median dialogue box height
  box_center_tolerance: 0.15          # deviation from median dialogue box center (fraction of band)
  max_duration_ms: 8000               # longer events are suspect
ocr_fix:
  batch_size: 50
  max_char_changes: 2
audio:
  sample_rate: 16000
  pad_ms: 100
  min_event_ms: 400
voice:
  model: speechbrain/spkrec-ecapa-voxceleb
  top_k: 3
  accept_score: 0.55
  min_margin: 0.08
  unknown_below: 0.35
  confusable_similarity: 0.75
  learn_from_reviews: true            # rebuild the voice bank from reviewed lines after each episode (5.8a)
  learn_min_ms: 800
  learn_trim_ms: 80
  learn_min_clips: 3
  learn_outlier_share: 0.1
  learn_from_auto: true               # auto-mode lines may teach, through the filter and gate (5.8a)
  learn_auto_min_score: 0.70
  learn_auto_min_margin: 0.15
  learn_auto_allowed_flags: [cps_exceeded, check_pinyin]
  learn_auto_min_test_lines: 30
  learn_auto_max_drop: 0.0
  new_voices: true                    # group unmatched voices into automatic characters (5.8)
  new_voice_below: 0.55
  new_voice_similarity: 0.60
  new_voice_known_max: 0.55
  new_voice_min_lines: 3
  new_voice_prefix: npc
cast:                                 # who is on screen / talking (5.8b)
  enabled: true
  detector_model: google/owlv2-base-patch16-ensemble
  embed_model: facebook/dinov2-base
  queries: [a cartoon character, a cartoon person, a cartoon fish, a dog]
  frame_width: 960                    # detection frames
  sample_fps: 5                       # decoding rate when picking each line's middle frame
  min_score: 0.15
  min_box_height: 0.12                # fractions of the frame
  min_box_width: 0.05
  max_box_width: 0.9
  nms_iou: 0.5
  match_similarity: 0.70              # closest exemplar of one character at least this similar...
  match_margin: 0.03                  # ...and this much closer than any other character's
  unknown_similarity: 0.75            # unrecognised crops this similar are one unknown sprite (per episode)
  motion_fps: 10
  motion_width: 480
  talk_dominance: 1.6                 # the talking sprite moves this many times more than any other
  learn: true
  name_min_votes: 3                   # an unknown sprite needs this many talking-line votes...
  name_min_share: 0.75                # ...this share of them for one character
  add_similarity: 0.85                # a recognition this sure joins the bank
  max_exemplars: 60                   # per character; the best-confirmed are kept
pinyin:
  polyphone_fallback: true
  polyphones: [了, 行, 长, 得, 还]
windows:
  gap_ms: 3000
  max_lines: 40
  context_overlap: 5
translate:
  max_retries: 2
  max_line_chars: 42
  max_lines_per_event: 2
  max_cps: 17
  retry_on_cps: false                 # false: reading speed is flagged for review, never retried
  picture_veto: "off"                 # off | recognised | any: a talking character on screen disputes the voice (5.11)
  picture_evidence: tiebreak          # all | tiebreak | off: which lines show the picture to the translator (5.11)
  pronoun_terms: []                   # pronoun words the rule check looks for; empty: the style's (5.11)
evaluate:
  min_score: 3                        # a criterion below this fails the line
  criteria: [meaning, pronouns, register, naturalness, speaker]
sprite:
  enabled: true
  match_threshold: 0.8
  scales: [0.6, 0.8, 1.0, 1.2]
  trigger_conf_below: 0.6
script_review:                        # whole-script pass before review (5.13a)
  enabled: true
  role: utility                       # one call per episode
  repeat_merge_gap_ms: 300            # identical text with at most this gap: one subtitle, merged
  repeat_window_ms: 4000              # a similar line within this time is flagged as a possible repeat
  repeat_similarity: 0.6
  remove_confidence: 0.9              # the model removes a line only this sure; otherwise it is flagged
  max_remove_share: 0.1               # safety cap: removals beyond this share of lines become flags
  example_limit: 30                   # reviewer decisions shown to the model, per kind
  memory_auto_remove_min: 2           # a short text removed this often and never kept is removed
  memory_max_han: 2                   # "short": at most this many Chinese characters
  fix_max_change_share: 0.5           # an OCR fix changes at most this share of the line (at least ocr_fix.max_char_changes)
  measure_words: "斤个天年月日号块元万千百米分秒点岁次条只位名人层倍级度两寸里"   # a 7 before these is a number
audit:                                # accuracy measured on a sample (6.11)
  sample_size: 20                     # random lines per audited episode
  min_per_stratum: 3                  # at least this many flagged and unflagged lines when available
  max_disagreements: 15               # plus lines where voice / picture / speaker disagree (reported separately)
  ignore_flags: [cps_exceeded, check_pinyin]   # flags that say nothing about correctness
  include_human: false                # human-reviewed episodes measure the reviewer, not the system
review:
  mode: human                         # human | auto
  predelete_fragments: true           # noisy OCR fragments arrive in review already deleted (restorable)
  noise_max_han: 2                    # "noisy": at most this many Chinese characters, or stray digits
memory:
  story_so_far_max_words: 600
  style_rules_max: 30
  dream_max_lines: 400                # approved lines sampled for dreaming
  correction_examples: 20             # recent reviewer corrections shown to translator and evaluator
  character_lifecycle: true           # keep / archive unlocked characters by appearances (5.15a)
  archive_after_absent: 2             # a one-off not seen for this many episodes is archived
  probation: true                     # a new character is a candidate until it comes back (5.15b)
  probation_min_lines: 3              # approved lines as speaker in its first episode
  probation_window: 2                 # it must come back within this many episodes (by number)
  character_updates: false            # one utility call per finished episode updates characters (5.15c)
  description_max_chars: 200          # a description the model writes is cut to this length
  aliases_max: 8                      # aliases kept per character
render:
  font_dir: fonts
  font_name: "Noto Sans"
  pinyin_font_size: 36                # at 1080p; scaled by video height
  vi_font_size: 48                    # at 1080p; scaled by video height
  pinyin_min_scale: 0.7               # shrink long pinyin lines down to this scale before wrapping
  line_spacing: 1.2
  avg_char_width: 0.55                # width estimate per character, as a share of font size
  outline: 2.5
  shadow: 0
  primary_color: "&H00FFFFFF"
  outline_color: "&H00000000"
  mask: blur                          # blur | box
  blur_radius: 20
  mask_color: black                   # box mask
  encoder: auto                       # auto (h264_nvenc if available) | h264_nvenc | libx264
  quality: 20                         # CRF for libx264, CQ for nvenc
llm:
  temperature: 0
  max_retries: 5
  timeout_s: 120
  max_retry_wait_s: 90
  providers:
    translator: {base_url: "https://api.deepseek.com", api_key_env: DEEPSEEK_API_KEY, model: "<verify>"}
    utility:    {base_url: "https://api.deepseek.com", api_key_env: DEEPSEEK_API_KEY, model: "<verify>"}
    evaluator:  {base_url: "https://generativelanguage.googleapis.com/v1beta/openai/", api_key_env: GEMINI_API_KEY, model: "<verify>"}
  prices: {}                          # per model, USD per 1M tokens: {input, input_cached, output}
budget:
  max_cost_per_episode: 1.00          # placeholder; set from the first episode's cost report
paths:
  work_dir: work                      # working files; relative to the project folder unless absolute
episodes:
  video_extensions: [.mp4, .mkv, .avi, .mov, .flv, .webm, .ts]
  number_patterns:                    # tried in order; first capture group is the episode number
    - '第\s*(\d+)\s*[集话話]'
    - '(?i)\bep(?:isode)?[\s._-]*(\d+)'
    - '(?i)\be(\d{1,4})\b'
    - '(\d{1,4})'
output:
  folder: null                        # required; set in Settings before the first render
  name_suffix: _vi                    # <source stem><suffix>.mp4
  on_exists: ask                      # ask (app) | overwrite | keep_both | fail (CLI default when non-interactive)
cleanup:
  auto: true                          # delete temporary files when an episode is done
baseline:
  name: null                          # set: every finished review is copied to <work>/_baseline/<name>/ (6.11d)
bench:
  baseline: null                      # the baseline the benchmark suite scores against (6.11e); null: baseline.name
```

Values above are the code defaults (`config.py`), except `number_patterns` (code default: only the last pattern). The project's `config.yaml` holds the tuned values; each tuned key carries a comment with the measurement behind it.

### 5.2a Series (`config.py`, `series.py`, `python -m subagent series …`)

The project can hold several series (shows). User decisions 2026-10-11: one folder per series, shared settings plus per-series overrides, one series active at a time (switch in the app or with `--series`).

- **Layout:** `data/series/<slug>/` per series: `memory/` (its own git repo), `bootstrap/` (cast, clips, sprites, `subtitle_style.json`, seed), `episodes/index.json`, `character_cards/` (card pins), `fonts/` (subtitle font; `render.font_dir` is relative to the series folder), `prompts/` (series notes) and `series.yaml`. **Throughout this spec, a path written `data/<x>` means the active series' folder `data/series/<slug>/<x>`.** Shared by every series: `config.yaml`, `.env`, `prompts/` (general prompts), `cache/` (LLM and model caches; character-card media in `cache/character_cards/<slug>/`), `app/fonts/` (the interface font). Without `data/series/` (no `series.default`) the single-series layout directly under `data/` still works (tests use it).
- **Config:** `config.yaml` holds the shared settings and `series.default`; the active series' `series.yaml` overrides any section (deep merge: mappings key by key, lists replaced) and the merged result is validated as one `Config`. The active series is `--series SLUG`, else `$SUBAGENT_SERIES`, else `series.default`. `migrate` moves the show-describing sections (`config.SERIES_SECTIONS`: show, video, ocr, non_dialogue, voice, cast, script_review, paths, baseline, bench) into series.yaml. Settings saved while a series is active (`save_settings` / `update_config_values`: the Settings screen, calibration) go to series.yaml when their section is one of those or already in series.yaml, else to config.yaml; values are rewritten **in place** (`subagent/yaml_edit.py`: only the value on the key's own line changes, a list or mapping becomes flow style on that line, missing keys are added at the end of their block, a mapping value replaces the mapping), so every comment, the order and blank lines stay; the merged result is validated before either file is written; the raw editor edits either file (`save_config_text(series_file=…)`), both validated merged.
- **Work folder:** a series without its own `paths.work_dir` works in `<config.yaml work_dir>/<slug>/`, so episode ids (`ep001`) never collide between series. Job locks, the baseline and bench runs live in it, so they are per series too.
- **Prompts:** the general prompt `prompts/<name>.md`, then the series' notes for it when `data/series/<slug>/prompts/<name>.md` exists, appended under `## Series notes` (`llm.load_prompt`). The stage input hash covers both (`pipeline._prompt_hash`). Show quirks belong in notes, not in the general prompt (series-1: `script_review_system.md`, the 了-drawn-as-7 font and the stray 楚 / 姬 / 史).
- **Commands:** `series list`, `series add SLUG [--name N] [--register R] [--work-dir D] (--identify-characters | --pronouns SELF ADDRESS)` (series.yaml with show name, translation style, character identification mode and default pronoun pair (5.11a; one of the two choices is required), which must exist in `prompts/registers/`, the bundled subtitle font from `app/fonts/`, empty bootstrap folders; then bootstrap as for the first series), `series default SLUG`, `series rename OLD NEW` (folder, card cache, default work folder, `series.default`), `series migrate SLUG` (single-series layout → a named series; folders and sections move, effective settings unchanged). Each refuses while a job of that series runs. config.yaml is edited as text, so comments stay.
