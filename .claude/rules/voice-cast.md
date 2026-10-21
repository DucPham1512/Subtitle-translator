---
paths:
  - "subagent/llm/client.py"
  - "subagent/voice/audio.py"
  - "subagent/voice/voice.py"
  - "subagent/cast/cast.py"
  - "subagent/cast/sprite.py"
  - "subagent/voice/learning.py"
  - "subagent/cast/learning.py"
  - "subagent/memory/characters.py"
  - "subagent/cast/card.py"
---
### 5.1 LLM client (`llm/client.py`)

- **Responsibility:** the only place that talks to LLM APIs.
- **Interface:** `call(role: Literal["translator","evaluator","utility"], messages, schema: type[BaseModel] | None, *, task: str = "") -> BaseModel | str`. `task` names the agent making the call (`translate`, `evaluate`, `script_review`, `ocr_fix`, `pinyin`, `briefing`, `bootstrap`, `dreaming`) for cost reporting.
- **Details:**
  - One `OpenAI` client per provider, built from config (`base_url`, `api_key_env`, `model`).
  - `temperature` from config, default 0.
  - JSON mode when `schema` is given. Validate with Pydantic. On validation failure, retry once with the validation error appended; on second failure raise `LLMOutputError`.
  - Retries with exponential backoff on network / 429 / 5xx errors, max `llm.max_retries`. A wait the provider asks for (`Retry-After`, Gemini's "retry in 37s") is honoured, up to `llm.max_retry_wait_s`. An exhausted per-day quota (Gemini free tier) is not retried: the call fails at once and says so.
  - Disk cache in `cache/llm/`, key = SHA-256 of (model, messages, schema name). A rerun with identical inputs costs nothing. `--no-cache` flag disables it.
  - Records usage per call to `work/<episode>/cost.jsonl` as a `CostRecord`: role, task, model, prompt tokens, cache-hit tokens (if reported), completion tokens, cost from `llm.prices` (USD per 1M tokens: `input`, `input_cached`, `output`). Thinking tokens count as completion (`max(completion, total - prompt)`).
  - A model without a price is recorded with `priced=false`, warned about once, and does not count toward the budget; once a price is configured its cost is recomputed from the stored tokens (`record_cost`). Status and report show such costs as incomplete (`+ ?`) and name the unpriced models.
  - Enforces `budget.max_cost_per_episode`: raise `BudgetExceeded` before a call that would start once the running total is over budget.
- **Prompt caching rule:** every prompt is assembled as `[static system prompt] + [memory prefix] + [variable content]`. The memory prefix is built once per episode and must be byte-identical across calls in that episode so the provider's prefix cache hits. Never put timestamps, counters or per-window data before the variable content.

### 5.7 Audio extraction (`voice/audio.py`)

- ffmpeg: `-vn -ac 1 -ar 16000` → `audio.wav`.
- Slicing happens in memory in the voice-match stage, using event timestamps plus `pad_ms`.

### 5.8 Voice match (`voice/voice.py`)

- **Responsibility:** propose the speaker for each event from audio.
- **Details:**
  - Load the SpeechBrain ECAPA model once.
  - For each event: slice audio, embed, L2-normalize, cosine similarity against every `voice_bank` centroid.
  - Status rules:
    - duration < `min_event_ms` → `too_short`
    - top-1 < `unknown_below` → `unknown`
    - top-1 ≥ `accept_score` and margin to top-2 ≥ `min_margin` and (top-1, top-2) not in `confusable_pairs` → `fixed`
    - otherwise → `confusable` with the top candidates
  - Log the share of each status in the report. This measures whether the sprite check is worth enabling.
- **New voices** (`voice.new_voices`, only when the voice bank is not empty):
  - Candidates: `unknown` / `confusable` lines whose top-1 < `new_voice_below` (a new character mostly scores as a low `confusable`, not `unknown`).
  - Group candidates by voice (`voice/voice.py: group_voices`, NumPy, deterministic): merge the two groups with the most similar mean voice while ≥ `new_voice_similarity`, then drop members below it.
  - A group with ≥ `new_voice_min_lines` lines whose mean voice scores < `new_voice_known_max` against every known character becomes a new voice with id `<new_voice_prefix>_<episode:03d>_<index:02d>` (e.g. `npc_005_01`). Its lines get status `new_voice` with that id as first candidate.
  - Written to `new_voices.json` (before `speakers.jsonl`). A missing file means no new voices.
  - **Returning candidates** (`memory.probation`, 5.15b): candidates first heard 1..`probation_window` episodes earlier are checked first. A pool line that sounds like one (≥ `accept_score` and ≥ `min_margin` above its best known character), or a group whose mean voice does (≥ `new_voice_similarity`), keeps the candidate's id (status `new_voice`); its `NewVoice` entry carries `returning_from` and the candidate's name. The prompt's new-voices block says "also heard in ep005 (named …)".
  - Every matched line's voice is saved to `voice_embeddings.npz` (kept by cleanup): a candidate's voice is built from it at finish.
- Archived characters (5.15a) are left out of the voice bank used for matching: the show reuses AI voices across minor characters, so an old one-off's voice would otherwise claim new characters.
- **Note:** subtitle events already segment the audio, so no diarization model is used.

### 5.8a Voice learning (`voice/learning.py`)

- **Trigger:** automatically after the memory update of every finished episode (both modes) when `voice.learn_from_reviews`; also `python -m subagent voices learn`. Never fails the episode.
- Rebuilds every centroid from the bootstrap clips plus approved dialogue lines ≥ `learn_min_ms` (trimmed by `learn_trim_ms`); a character needs `learn_min_clips` samples; with ≥ 10 samples the least typical `learn_outlier_share` is dropped. Recomputes confusable pairs. Written through the Memory Manager.
- **Human-mode episodes** (`state.json` mode `human`): every approved line with a known speaker counts.
- **Auto-mode episodes** count only through:
  1. Filter: voice status `fixed` or `new_voice`, top-1 ≥ `learn_auto_min_score`, margin ≥ `learn_auto_min_margin`, the translator kept that speaker, first-attempt evaluation passed, no flags outside `learn_auto_allowed_flags`. The translator's `speaker_conf` is not used (it copies the voice score).
  2. Gate: leave-one-episode-out top-1 accuracy on human-reviewed lines, with and without the auto lines. Used only if there are ≥ `learn_auto_min_test_lines` test lines and accuracy does not drop more than `learn_auto_max_drop`. The decision and both accuracies appear in the job message and the memory commit.
- `python -m subagent voices evaluate`: leave-one-episode-out accuracy on human-reviewed lines, per status, plus an `accept_score` / `min_margin` sweep. Writes nothing.

### 5.8b Cast: who is on screen and who is talking (`cast/cast.py`, `cast/learning.py`)

- **Stage (per event, `cast.enabled`):**
  - The middle frame (decoded once per episode at `sample_fps`, `frame_width` wide) goes through OWLv2 with `cast.queries`; boxes are filtered by `min_score` and size, then non-maximum suppression (a box mostly inside a kept one is dropped).
  - Each crop is described by DINOv2 (L2-normalized). It is named when its closest sprite-bank exemplar of one character is ≥ `match_similarity` and ≥ `match_margin` closer than any other character's; archived characters are left out of the bank. Unrecognised crops are grouped per episode into unknown sprites (`u001`, ...; `unknown_similarity`).
  - With 2+ characters on screen, the line is decoded at `motion_fps` / `motion_width`; the camera's pan/zoom between frames is estimated (feature tracking + RANSAC partial affine) and cancelled; the mean remaining movement in each box's upper half (head) is its motion. The talking sprite is the one moving ≥ `talk_dominance` times more than every other; none otherwise. A lone character gets no talking claim (the speaker may be off screen).
  - Output `cast.jsonl` (`CastLine`), `cast_embeddings.npy`, and `cast_frames/<event>.jpg`: the exact frame analysed per line (temporary, about 15 MB per episode; review and learning use it so boxes line up even on moving characters; deleted by cleanup, after which the review falls back to the video frame at the same time). Counts: characters, recognised, unknown sprites, talking lines.
- **Use:** translator input per line: `on_screen` (recognised ids), `unrecognised_on_screen`, `talking` (id or `unrecognised`), as evidence like the voice, never a decision (5.11).
- **Learning (after the episode's memory update and voice learning; `cast.learn`; never fails the episode; skipped when cast and approved script are unchanged):**
  - Trusted speakers: every approved dialogue line in human mode; in auto mode only lines every independent signal agrees on (`memory/evidence.trusted_auto_lines`, the voice auto filter).
  - For each trusted line with a talking sprite: recognised as the speaker → its exemplar gains a `right`; recognised as someone else → its exemplar gains a `wrong` and the sprite counts as unknown. Exemplars with more wrongs than rights are removed.
  - An unknown talking sprite votes for the speaker; an unknown sprite with ≥ `name_min_votes` votes and ≥ `name_min_share` for one character becomes that character (3 passes, as each name explains more lines). Its crops join the bank.
  - Reviewer box edits come first (`ReviewedLine.cast_*`, made in the review screen's On screen view, 6.4; `cast/learning.apply_review_edits`): moved/resized boxes and boxes drawn around missed characters (with a character chosen) are cut from the analysed frame and described again (the image model loads only for this; skipped with a log message when it cannot); the reviewer's talking mark replaces the detected talker (`none`: nobody on screen talks), and a box marked talking on a line with a trusted speaker is labelled as that speaker unless named explicitly.
  - Reviewer box labels (`ReviewedLine.cast_labels`) come first: a labelled box is that character (its crop joins the bank; the exemplar that had named it differently gains a `wrong`, one that named it right a `right`); a box labelled `_none` (not a character) is never learned and never votes. Labelled boxes are left out of the talking-line corrections and votes.
  - Recognitions ≥ `add_similarity` and confirmed talkers join the bank (new poses). Each character keeps its `max_exemplars` best-confirmed exemplars (right − wrong, then newest).
  - Written through `MemoryManager.write_sprites` in one transaction, one `memory_log` row per character, commit `sprites from <ep>: +n, -m, k new names, c corrections`. Deleting a character deletes its sprites. Re-finish safe: each episode's votes and added exemplars are recorded (`sprite_feedback`); learning the episode again first takes them back (its additions deleted, its votes subtracted) and plans against the bank without them. An exemplar its votes removed cannot come back.
- **Backfill:** `python -m subagent sprites learn` runs the cast stage on finished episodes that lack it, then learns from each, in episode order.
- **Tests** never load the models: `tests/conftest.py` turns `cast.enabled` off and sets `HF_HUB_OFFLINE=1`; cast tests use a fake detector, image model, frames and motion.

### 5.13 Sprite check (`cast/sprite.py`, optional)

- **Responsibility:** resolve low-confidence speaker choices between candidates using on-screen art.
- **Trigger:** `sprite.enabled` and flag `low_speaker_conf`.
- **Details:**
  - Extract one full frame at the event midpoint with `ffmpeg -ss <t> -frames:v 1`.
  - For each candidate, run grayscale `cv2.matchTemplate` (TM_CCOEFF_NORMED) with each template at each scale in `sprite.scales`; take the max.
  - Exactly one candidate above `match_threshold` → set that speaker, clear the flag. Otherwise flag `sprite_unresolved` (sent to human review).
  - Log how often it triggers and resolves.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/decisions/đo lường - nhận diện nhân vật và giọng.md`.
