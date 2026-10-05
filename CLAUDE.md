# CLAUDE.md — Subtitle Agent

Implementation guide for Claude Code. Read this fully before writing code. When this file and a request conflict, ask before deviating.

## 1. Project overview

A local Python pipeline that translates the burned-in Chinese subtitles (hardsubs) of one specific cartoon series into Vietnamese, adds pinyin, and renders the result back onto the video.

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

## 3. Architecture

### 3.1 Pipeline

```
                ┌──────────────────────── Subtitle Parser ─────────────────────────┐
Video ─────────►│ frame sampling + change detection → OCR → OCR correction → events │
  │             └──────────────────────────────────────────────────────┬───────────┘
  │                                                                    │ events (zh, timestamps)
  ├─► audio extraction ─► voice match per event ─► confusable pair? ───┤
  ├─► cast: characters on screen + talking sprite per event (5.8b) ───┤
  │                         (top-k candidates)                         │
  │                                                                    ▼
  │                                  Translator (scene window + speaker/listener inference)
  │                                         ▲            │
  │                              retry ≤2   │            ▼
  │                                         └──── Evaluator (rule checks + LLM rubric)
  │                                                      │ low speaker confidence
  │                                                      ├──────────► Sprite check (optional)
  │                                                      ▼                  │
  │                    Script review (whole episode: repeats, noise) ◄──────┘ (resolved)
  │                                                      │
  │          events ─► Pinyin ─────────────────────► Review gate
  │                                                 human │ auto
  │                                                       ▼
  │                                  Human review (app) → Approved script + edits
  │                                                       │
  │                         ┌─────────────────────────────┼──────────────────┐
  │                         ▼                             ▼                  │
  │                  Memory Manager (sole writer)   Output renderer          │
  │                  → voice learning               ASS → mask → burn-in ────┴─► final video
  │                         ▲
  │                  Dreaming (offline, between episodes)
  │
Memory bootstrap (before episode 1) ─► human review ─► Memory Manager
```

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

## 4. Data models

Defined in `subagent/models.py`. All JSONL artifacts are one serialized model per line.

```python
class Episode(BaseModel):
    id: str                    # "ep003", from the confirmed episode number (zero-padded to 3)
    number: int
    source_path: str           # absolute path; the video is never copied
    source_size: int
    source_mtime: float
    source_fingerprint: str    # SHA-256 of size + first 1 MB + last 1 MB
    added_at: str
    status: Literal["new", "running", "awaiting_review", "done", "failed", "missing"] = "new"
    output_path: str | None = None

class SubtitleEvent(BaseModel):
    id: str                    # "<episode_id>:<index:04d>"
    start_ms: int
    end_ms: int
    zh_raw: str                # OCR output, merged across frames
    zh: str                    # after OCR correction
    ocr_conf: float            # mean OCR confidence
    ocr_fixed: bool = False
    flags: list[str] = []      # non_dialogue_suspect, ocr_uncertain, ocr_low_conf, ocr_fragment
    notes: list[str] = []      # reasons behind flags, OCR fix reasons
    box_height / box_vcenter / box_hcenter: float | None   # reading geometry, fractions of the band
    multi_row: bool = False

class SpeakerCandidates(BaseModel):
    event_id: str
    candidates: list[tuple[str, float]] = []   # (character_id, cosine score), top-k, sorted
    status: Literal["fixed", "confusable", "unknown", "too_short", "new_voice", "disputed"]   # disputed: set by the picture veto (5.11)

class NewVoice(BaseModel):              # new_voices.json: lines that sound alike but match no known character
    id: str                             # "npc_005_01": `voice.new_voice_prefix`, episode number, voice index
    event_ids: list[str]
    cohesion: float                     # mean similarity of the lines to their average voice
    closest_known: str | None = None
    closest_score: float = 0.0
    returning_from: str | None = None   # a candidate (5.15b) first heard in that episode, heard again here
    name_vi: str | None = None          # the candidate's name, when the dialogue gave one

class CastDetection(BaseModel):         # one character in a line's middle frame (cast.jsonl, 5.8b)
    index: int                          # row in cast_embeddings.npy
    box: list[float]                    # x0, y0, x1, y1 in the detection frame (cast.frame_width wide)
    score: float
    label: str                          # the detector query that found it
    character: str | None = None        # recognised from the sprite bank
    similarity: float = 0.0
    unknown: str | None = None          # per-episode unknown sprite ("u001") when not recognised
    motion: float | None = None         # head-area movement with camera pan/zoom cancelled

class CastLine(BaseModel):              # cast.jsonl
    event_id: str
    detections: list[CastDetection] = []
    talking: int | None = None          # position of the clearly talking sprite in `detections`

class ScriptDecision(BaseModel):        # script_review.jsonl (5.13a)
    event_id: str
    action: Literal["remove", "flag", "fix"]       # fix: real dialogue whose Chinese has an OCR error
    reason: Literal["repeat", "noise", "unrelated", "other", "ocr"]
    source: Literal["rule", "memory", "llm"]
    confidence: float = 1.0
    note: str = ""
    keep_id: str | None = None          # repeats: the line that stays and takes over the removed line's time
    zh_fix: str | None = None           # fix: the suggested corrected Chinese (never applied automatically)
    evidence: str = ""                  # fix: the model's context check

class LineTranslation(BaseModel):
    event_id: str
    speaker: str | None
    listener: str | None
    speaker_conf: float        # 0..1, from translator (in practice close to the voice score)
    line_type: Literal["dialogue", "sign", "title", "sfx"] = "dialogue"
    vi: str
    attempts: int
    flags: list[str] = []      # retry_cap, low_speaker_conf, sprite_unresolved, cps_exceeded, speaker_override, ...
    proposals: list[MemoryProposal] = []
    notes: str = ""

class Evaluation(BaseModel):
    event_id: str
    attempt: int
    passed: bool
    scores: dict[str, int] = {}     # criterion -> 1..5
    feedback: str = ""
    rule_failures: list[str] = []   # hard failures: the line is retried
    soft_failures: list[str] = []   # flagged for review only (reading speed unless translate.retry_on_cps)
    suggestion: str = ""            # evaluator's corrected line when it failed

class ReviewedLine(BaseModel):
    event_id: str
    start_ms: int
    end_ms: int
    speaker: str | None
    listener: str | None
    zh: str
    pinyin: str
    vi: str
    line_type: Literal["dialogue", "sign", "title", "sfx"] = "dialogue"
    pinyin_overridden: bool = False
    approved: bool = False
    edited: bool = False
    flags: list[str] = []
    deleted: bool = False      # removed in review: not rendered, not memory evidence, restorable until finished
    cast_labels: dict[str, str] = {}   # reviewer's box corrections: detection position -> character id or "_none"
    cast_boxes: dict[str, list[float]] = {}   # moved/resized detected boxes, by position (cast-frame coordinates)
    cast_added: list[CastBoxEdit] = []        # boxes drawn around missed characters: {box, character}
    cast_talking: str | None = None           # reviewer's talking sprite: position, "a<i>" (drawn box) or "none"
    cast_checked: bool = False                # reviewer checked On screen: boxes left alone are confirmed (gold)

class EditRecord(BaseModel):   # edits.jsonl
    edit_id: str               # "<event_id>:<field>"
    event_id: str
    field: str                 # zh | pinyin | vi | speaker | listener | line_type | deleted | cast_labels | cast_boxes | cast_added | cast_talking | cast_checked
    before: str | None
    after: str | None

class MemoryProposal(BaseModel):
    kind: Literal["glossary", "pronoun_pair", "character", "style_rule", "briefing", "line_decision"]
    payload: dict
    source: Literal["translator", "human", "bootstrap", "dreaming"]
    evidence: list[str] = []   # event ids or edit ids

class CostRecord(BaseModel):   # cost.jsonl, one per LLM call (5.1)
    ts: str
    role: str
    model: str
    prompt_tokens: int = 0
    cache_hit_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    cached_response: bool = False   # served from the local disk cache
    task: str = ""                  # the agent: translate, evaluate, script_review, ocr_fix, pinyin, briefing, ...
    priced: bool | None = None      # False: no price when the call was made; repriced once one is configured
```

Other models in `models.py`: `VideoInfo`, `ChangeRecord`, `OcrBox`, `OcrReading`, `PinyinLine`, `Window`, `StageState`, `EpisodeState`, `CastBoxEdit` (5.8b), `PartialSuggestion` (6.4b), `AuditSample` / `AuditMark` (6.11; aspects `AUDIT_ASPECTS` = speaker, ocr, translation, pronouns; `AuditMark.na` lists aspects marked not applicable).

### 4.1 SQLite schema (`data/memory/memory.db`)

```sql
CREATE TABLE characters (
  id TEXT PRIMARY KEY,            -- stable slug, e.g. "xiao_ming"
  name_zh TEXT NOT NULL,
  name_vi TEXT NOT NULL,          -- Hán-Việt reading
  description TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',   -- active | kept | archived (5.15a)
  status_note TEXT,                        -- why the status was set
  generic INTEGER NOT NULL DEFAULT 0       -- many individuals under one name (all fish, passers-by)
);

CREATE TABLE appearances (         -- who appears in which episode (5.15a)
  character_id TEXT NOT NULL,
  episode_id TEXT NOT NULL,
  lines INTEGER NOT NULL,          -- approved lines with the character as speaker or listener
  PRIMARY KEY (character_id, episode_id)
);

CREATE TABLE glossary (
  zh TEXT PRIMARY KEY,
  vi TEXT NOT NULL,
  pinyin TEXT,
  type TEXT,                      -- name | title | place | sect | realm | technique | item | term | idiom
  notes TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL,
  first_episode TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE pronoun_pairs (
  speaker_id TEXT NOT NULL REFERENCES characters(id),
  listener_id TEXT NOT NULL REFERENCES characters(id),
  self_term TEXT NOT NULL,        -- how speaker refers to self, e.g. "em"
  address_term TEXT NOT NULL,     -- how speaker addresses listener, e.g. "anh"
  context TEXT NOT NULL DEFAULT '',  -- optional condition, e.g. "when angry"; '' = default pair
  since_episode TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (speaker_id, listener_id, context)
);

CREATE TABLE voice_bank (
  character_id TEXT PRIMARY KEY REFERENCES characters(id),
  embedding BLOB NOT NULL,        -- float32 centroid, L2-normalized
  n_clips INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE confusable_pairs (
  a TEXT NOT NULL, b TEXT NOT NULL,   -- a < b
  similarity REAL NOT NULL,
  PRIMARY KEY (a, b)
);

CREATE TABLE memory_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  op TEXT NOT NULL,               -- insert | update | delete | rejected
  tbl TEXT NOT NULL,
  key TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  source TEXT NOT NULL,
  reason TEXT,
  commit_sha TEXT,               -- filled when the memory folder is committed
  evidence_count INTEGER NOT NULL DEFAULT 0   -- used by the conflict rule (more evidence wins)
);

-- Columns added after the first release are added to an existing memory.db by `store.migrate` (ALTER TABLE).

CREATE TABLE sprite_bank (        -- how each character looks (5.8b)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id TEXT NOT NULL,
  embedding BLOB NOT NULL,         -- float16, L2-normalized DINOv2 features of one crop
  episode_id TEXT, event_id TEXT,
  right INTEGER NOT NULL DEFAULT 0,  -- times it named the reviewed speaker of a talking sprite
  wrong INTEGER NOT NULL DEFAULT 0,  -- times it named someone else
  added_at TEXT NOT NULL
);

CREATE TABLE line_decisions (     -- the script reviewer's memory (5.13a)
  zh TEXT PRIMARY KEY,            -- normalized Chinese text of a line
  remove_count INTEGER NOT NULL DEFAULT 0,   -- times the reviewer removed a line with this text
  keep_count INTEGER NOT NULL DEFAULT 0,     -- times the reviewer kept it (short lines, restored lines)
  last_episode TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE candidates (         -- new characters on probation (5.15b)
  id TEXT PRIMARY KEY,            -- npc_005_02, or the id the translator proposed
  first_episode TEXT NOT NULL,
  name_zh TEXT, name_vi TEXT, description TEXT,
  embedding BLOB,                 -- float32 voice of its approved lines (from voice_embeddings.npz), may be missing
  n_lines INTEGER NOT NULL,       -- approved lines it speaks in the first episode
  pending_json TEXT NOT NULL DEFAULT '[]',   -- proposals waiting for the promotion (pronoun pairs)
  status TEXT NOT NULL DEFAULT 'candidate',  -- candidate | promoted | dropped
  status_note TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE candidate_sprites (  -- a candidate's unrecognised talking sprites (float16 DINOv2 features)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL, embedding BLOB NOT NULL, episode_id TEXT, event_id TEXT
);

-- Re-finish safety: one episode's share of learning, replaced when its review is finished again.
CREATE TABLE line_decision_episodes (zh TEXT, episode_id TEXT, removed INTEGER, kept INTEGER, PRIMARY KEY (zh, episode_id));
CREATE TABLE sprite_feedback (     -- votes one episode gave an exemplar; added = 1: it added the exemplar
  exemplar_id INTEGER, episode_id TEXT, right INTEGER, wrong INTEGER, added INTEGER, PRIMARY KEY (exemplar_id, episode_id)
);
```

### 4.2 Markdown memory (`data/memory/`)

- `briefings/INDEX.md`: index at the top of the folder. One line per episode: episode id, one-sentence summary, characters introduced, file name. Read this first to decide which episode files to open.
- `briefings/story_so_far.md`: rolling summary, capped at `memory.story_so_far_max_words`.
- `briefings/<episode_id>.md`: per-episode summary, new characters, relationship changes, key terms.
- `style_rules.md`: style rules (word order, dropped vocatives, tone, punctuation) with one example each, mined from human edits by dreaming, capped at `memory.style_rules_max`. Term translations never go here; they belong in the glossary.

Other files in `data/memory/` (all versioned by git):

- `conflicts.json` (+ rendered `conflicts.md`): proposals that lost the conflict rule, resolved in the app (6.7).
- `speaker_corrections.jsonl`: speaker / listener changes made in review, input for dreaming.
- `dream_proposals.json`, `dream_state.json`: the last dreaming run and which edits it has seen.
- `dream_rejections.json`: proposals the reviewer rejected; dreaming never proposes them again (5.18).

## 5. Components

Each component lists: responsibility, inputs, outputs, implementation details, config keys, failure handling.

### 5.1 LLM client (`llm.py`)

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

### 5.2 Config (`config.py`, `config.yaml`)

Pydantic-validated. Every threshold in this document is a config key; no magic numbers in code. Example:

```yaml
show:
  name: "<show name>"
  genre_register: "co_trang_tien_hiep"  # drives translator register instructions
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
  pronoun_terms: []                   # Vietnamese pronoun words the pronoun rule check looks for
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
```

Values above are the code defaults (`config.py`), except `number_patterns` (code default: only the last pattern). The project's `config.yaml` holds the tuned values; each tuned key carries a comment with the measurement behind it.

### 5.3 Frame sampling + change detection (`stages/ingest.py`)

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

### 5.4 OCR (`stages/ocr.py`)

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

### 5.4a Generic subtitle segmentation (`subtitle_style.py`, `ocr.preprocess: segment`)

- **Why:** the tool is meant for many cartoon series (user goal), so nothing may be tuned to one show's font. A subtitle is text whose strokes have nearly constant width, that stays still while the scene behind it changes, and whose style stays the same through a series.
- **Calibration, once per series** (user decision 2026-10-03; `python -m subagent calibrate EPISODE --style`, or the bootstrap wizard's Calibrate step, 6.6): bands sampled across one episode (`video.calibrate_fps`, at most `calibrate_max_bands`). Candidate regions come from MSER and from connected components at a few grey levels (Otsu and fixed steps; threshold-based), in both polarities; the stroke-width transform (edge-based: Canny edges paired across each stroke along the gradient, rays capped at a third of the band height) measures their stroke widths. Text-like regions (letter-sized, stroke widths consistent, unchanged between consecutive samples) are kept. The polarity whose regions are consistently set off from their surroundings wins (an outline, itself a constant-width stroke, has fill on one side and background on the other); with an outline, only outlined regions are learned from. Saved to `data/bootstrap/subtitle_style.json` (series data, not `config.yaml`, which would lose its comments): polarity, fill grey range (two thirds of the way from the outline to the fill, leaving room for compression), outline level, stroke width and letter height as shares of the band height. A preview (band above, segmentation below) goes to `work/<episode>/calibration/style.png`. With `preprocess: segment` the OCR stage's input hash includes the style's values (not its date or region count), so a new calibration re-reads the subtitles of every episode run afterwards; other pre-processing never reads it.
- **Segmentation, every band:** fill-range components (threshold) whose median SWT stroke width is within `seg_stroke_tolerance` of the series', at most `seg_max_height` / `seg_max_width` letter heights, ringed by the outline for at least `seg_outline_share` of their surroundings when the style has one, and at least `seg_min_stable` still when ingest saved a stability map. Region growing then adds neighbouring components on the same rows that pass every test but the stroke width (letters at a line's ends still widen the line). The result feeds line grouping, cropping and recognition like the show-tuned mask.
- **Outline level:** a quarter of the way from the outline's typical grey towards the fill (compression lightens outlines unevenly; at the typical grey letters measured only 45–57% outlined and end letters were dropped). With `seg_outline_share` 0.4, letters measured 56–77% and scenery at most 16%.
- **This show** (ep005): light text, fill 168–255, outline 72 (typical grey 14), stroke 0.125 and letter height 0.77 of the band.
- **In use** (user decision 2026-10-03): the project's `config.yaml` sets `ocr.preprocess: segment`, `recognize: line`, `mask_image: original`, `mask_scale: 1.0`, `symmetric_crop: true` (tolerance 0.75) and `video.band_frames: 5` (code defaults stay off, since segmentation needs a calibrated style). `python -m subagent check` reports a missing style; tests reset these keys (`tests/conftest.py`). Generality can only be measured on a second series with its own answer key.

### 5.5 Event building (`stages/events.py`)

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

### 5.6 OCR correction (`stages/ocr_fix.py`)

- **Responsibility:** fix OCR character errors (similar-looking characters) using context and the glossary.
- **Details:**
  - Batches of `ocr_fix.batch_size` events, sent to the `utility` role with the glossary (zh terms only) in the memory prefix.
  - The model returns only the lines it changes, with a reason.
  - Code rejects any change over `max_char_changes` characters, and adds flag `ocr_uncertain` instead.
  - Output `events.jsonl` with `zh` and `ocr_fixed`.

### 5.7 Audio extraction (`stages/audio.py`)

- ffmpeg: `-vn -ac 1 -ar 16000` → `audio.wav`.
- Slicing happens in memory in the voice-match stage, using event timestamps plus `pad_ms`.

### 5.8 Voice match (`stages/voice.py`)

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
  - Group candidates by voice (`stages/voice.py: group_voices`, NumPy, deterministic): merge the two groups with the most similar mean voice while ≥ `new_voice_similarity`, then drop members below it.
  - A group with ≥ `new_voice_min_lines` lines whose mean voice scores < `new_voice_known_max` against every known character becomes a new voice with id `<new_voice_prefix>_<episode:03d>_<index:02d>` (e.g. `npc_005_01`). Its lines get status `new_voice` with that id as first candidate.
  - Written to `new_voices.json` (before `speakers.jsonl`). A missing file means no new voices.
  - **Returning candidates** (`memory.probation`, 5.15b): candidates first heard 1..`probation_window` episodes earlier are checked first. A pool line that sounds like one (≥ `accept_score` and ≥ `min_margin` above its best known character), or a group whose mean voice does (≥ `new_voice_similarity`), keeps the candidate's id (status `new_voice`); its `NewVoice` entry carries `returning_from` and the candidate's name. The prompt's new-voices block says "also heard in ep005 (named …)".
  - Every matched line's voice is saved to `voice_embeddings.npz` (kept by cleanup): a candidate's voice is built from it at finish.
- Archived characters (5.15a) are left out of the voice bank used for matching: the show reuses AI voices across minor characters, so an old one-off's voice would otherwise claim new characters.
- **Note:** subtitle events already segment the audio, so no diarization model is used.

### 5.8a Voice learning (`memory/voice_learning.py`)

- **Trigger:** automatically after the memory update of every finished episode (both modes) when `voice.learn_from_reviews`; also `python -m subagent voices learn`. Never fails the episode.
- Rebuilds every centroid from the bootstrap clips plus approved dialogue lines ≥ `learn_min_ms` (trimmed by `learn_trim_ms`); a character needs `learn_min_clips` samples; with ≥ 10 samples the least typical `learn_outlier_share` is dropped. Recomputes confusable pairs. Written through the Memory Manager.
- **Human-mode episodes** (`state.json` mode `human`): every approved line with a known speaker counts.
- **Auto-mode episodes** count only through:
  1. Filter: voice status `fixed` or `new_voice`, top-1 ≥ `learn_auto_min_score`, margin ≥ `learn_auto_min_margin`, the translator kept that speaker, first-attempt evaluation passed, no flags outside `learn_auto_allowed_flags`. The translator's `speaker_conf` is not used (it copies the voice score).
  2. Gate: leave-one-episode-out top-1 accuracy on human-reviewed lines, with and without the auto lines. Used only if there are ≥ `learn_auto_min_test_lines` test lines and accuracy does not drop more than `learn_auto_max_drop`. The decision and both accuracies appear in the job message and the memory commit.
- `python -m subagent voices evaluate`: leave-one-episode-out accuracy on human-reviewed lines, per status, plus an `accept_score` / `min_margin` sweep. Writes nothing.

### 5.8b Cast: who is on screen and who is talking (`stages/cast.py`, `memory/sprite_learning.py`)

- **Why:** voice alone cannot separate the show's many minor characters, and the show reuses AI voices between them. The picture can: characters are recognisable by costume across episodes, and the talking sprite is the one that moves.
- **Stage (per event, `cast.enabled`):**
  - The middle frame (decoded once per episode at `sample_fps`, `frame_width` wide) goes through OWLv2 with `cast.queries`; boxes are filtered by `min_score` and size, then non-maximum suppression (a box mostly inside a kept one is dropped).
  - Each crop is described by DINOv2 (L2-normalized). It is named when its closest sprite-bank exemplar of one character is ≥ `match_similarity` and ≥ `match_margin` closer than any other character's; archived characters are left out of the bank. Unrecognised crops are grouped per episode into unknown sprites (`u001`, ...; `unknown_similarity`).
  - With 2+ characters on screen, the line is decoded at `motion_fps` / `motion_width`; the camera's pan/zoom between frames is estimated (feature tracking + RANSAC partial affine) and cancelled; the mean remaining movement in each box's upper half (head) is its motion. The talking sprite is the one moving ≥ `talk_dominance` times more than every other; none otherwise. A lone character gets no talking claim (the speaker may be off screen).
  - Output `cast.jsonl` (`CastLine`), `cast_embeddings.npy`, and `cast_frames/<event>.jpg`: the exact frame analysed per line (temporary, about 15 MB per episode; review and learning use it so boxes line up even on moving characters; deleted by cleanup, after which the review falls back to the video frame at the same time). Counts: characters, recognised, unknown sprites, talking lines.
- **Use:** translator input per line: `on_screen` (recognised ids), `unrecognised_on_screen`, `talking` (id or `unrecognised`), as evidence like the voice, never a decision (5.11).
- **Learning (after the episode's memory update and voice learning; `cast.learn`; never fails the episode; skipped when cast and approved script are unchanged):**
  - Trusted speakers: every approved dialogue line in human mode; in auto mode only lines every independent signal agrees on (`voice_learning.trusted_auto_lines`, the voice auto filter).
  - For each trusted line with a talking sprite: recognised as the speaker → its exemplar gains a `right`; recognised as someone else → its exemplar gains a `wrong` and the sprite counts as unknown. Exemplars with more wrongs than rights are removed.
  - An unknown talking sprite votes for the speaker; an unknown sprite with ≥ `name_min_votes` votes and ≥ `name_min_share` for one character becomes that character (3 passes, as each name explains more lines). Its crops join the bank.
  - Reviewer box edits come first (`ReviewedLine.cast_*`, made in the review screen's On screen view, 6.4; `sprite_learning.apply_review_edits`): moved/resized boxes and boxes drawn around missed characters (with a character chosen) are cut from the analysed frame and described again (the image model loads only for this; skipped with a log message when it cannot); the reviewer's talking mark replaces the detected talker (`none`: nobody on screen talks), and a box marked talking on a line with a trusted speaker is labelled as that speaker unless named explicitly.
  - Reviewer box labels (`ReviewedLine.cast_labels`) come first: a labelled box is that character (its crop joins the bank; the exemplar that had named it differently gains a `wrong`, one that named it right a `right`); a box labelled `_none` (not a character) is never learned and never votes. Labelled boxes are left out of the talking-line corrections and votes.
  - Recognitions ≥ `add_similarity` and confirmed talkers join the bank (new poses). Each character keeps its `max_exemplars` best-confirmed exemplars (right − wrong, then newest).
  - Written through `MemoryManager.write_sprites` in one transaction, one `memory_log` row per character, commit `sprites from <ep>: +n, -m, k new names, c corrections`. Deleting a character deletes its sprites. Re-finish safe: each episode's votes and added exemplars are recorded (`sprite_feedback`); learning the episode again first takes them back (its additions deleted, its votes subtracted) and plans against the bank without them. An exemplar its votes removed cannot come back.
- **Measured (replay of ep001–005 with reviewed speakers):** talking sprite named right 4/5, 6/14, 29/39, 29/33 (ep002–ep005); speaker among recognised characters 25–38% of lines; coverage grows with the bank. Main-cast libraries clean except pairs who always appear and move together.
- **Backfill:** `python -m subagent sprites learn` runs the cast stage on finished episodes that lack it, then learns from each, in episode order.
- **Tests** never load the models: `tests/conftest.py` turns `cast.enabled` off and sets `HF_HUB_OFFLINE=1`; cast tests use a fake detector, image model, frames and motion.

### 5.9 Pinyin (`stages/pinyin_gen.py`)

- **Responsibility:** deterministic pinyin for corrected Chinese.
- **Details:**
  - Load glossary names into jieba's user dictionary and their pinyin into pypinyin's phrase dictionary, so names are segmented and read correctly.
  - `pypinyin.lazy_pinyin(..., style=Style.TONE)` over jieba segments; join syllables within a word, space between words.
  - Polyphone fallback: a small config list of high-risk characters (e.g. 了, 行, 长, 得, 还) that occur outside a known phrase are sent in one batched `utility` call per episode. Everything else stays deterministic.
  - Regenerate pinyin for any line whose `zh` a human edits.

### 5.10 Scene windowing (`stages/windows.py`)

- Split events into windows at gaps > `windows.gap_ms` or at `windows.max_lines`.
- Each window carries `context_overlap` previous lines (already translated) as read-only context.

### 5.11 Translator (`stages/translate.py`)

- **Responsibility:** translate a window into Vietnamese and decide speaker and listener per line.
- **Prompt layout:**
  1. Static system prompt (`prompts/translator_system.md`): subtitle style, register from `show.genre_register`, xưng hô rules, length limits, output schema.
  2. Memory prefix (built once per episode): characters (archived ones left out), full glossary, pronoun matrix (pairs with archived characters left out), `story_so_far.md`, `style_rules.md`, then the episode's new voices (id, line count, first time) and the known characters without a voice sample.
  3. Variable: previous context lines, then window lines as JSON with `event_id`, `zh`, `speaker_candidates` and their status.
- **Output per line:** `speaker`, `listener`, `speaker_conf`, `vi`, optional `proposals` (new glossary terms, new or changed pronoun pairs, new characters) with evidence event ids.
- **Rules given to the model:**
  - `fixed` speaker: keep it unless the dialogue makes it impossible, then say why in `notes`.
  - `confusable`: choose between the listed candidates only.
  - `disputed` (picture veto, `translate.picture_veto`): before translation, a line whose voice match is `fixed` / `new_voice` / `confusable` becomes `disputed` when the clearly talking sprite (5.8b) is a recognised character other than the voice's top candidate (or, for `confusable`, not among its candidates); with `any`, also when the talker is unrecognised (`fixed` / `new_voice` only). The recognised talker is added to the candidates. The translator chooses between the candidates by the dialogue, or leaves the speaker null when neither fits; it does not follow the voice by default. Off by default: measured on ep007–011 (100 gold lines), speaker accuracy off 78.5%, recognised 78.7%, any 77.4%; on voice/picture disagreement lines 47 / 37 / 33%. The veto fixed the shared-voice cases but the picture named the wrong talker as often, so it waits for better talking-sprite recognition.
  - `new_voice`: keep the new voice id unless the dialogue shows it is a known character (e.g. one without a voice sample).
  - `unknown` / `too_short`: choose a character present in the scene only when the dialogue makes it clear; otherwise speaker null. Never guess.
  - Speaker / listener ids: the Characters table or the episode's new voices (rule checks accept both).
  - An automatic character (`npc_…`) whose identity the dialogue reveals (name, title, role, form of address): propose a `character` with the same id and `name_zh`, `name_vi`, `description`. Never a new id.
  - Use the pronoun matrix for the (speaker, listener) pair. If no pair exists, propose one.
  - Glossary terms must be used exactly.
  - `on_screen` / `unrecognised_on_screen` / `talking` (5.8b): weak evidence, weaker than the voice and the dialogue (user decision 2026-10-02: the talking sprite made the translator override sure voices). Never a reason to change a `fixed` or `new_voice` speaker; a tie-breaker between `confusable` candidates, or for `unknown` / `too_short` lines together with a clear dialogue clue; never a speaker from the picture alone. With `translate.picture_evidence: tiebreak` (default) the picture fields are left out of `fixed` / `new_voice` lines entirely; `all` shows them everywhere, `off` nowhere.
  - `non_dialogue_suspect`: decide whether the line is dialogue. If not, set `line_type` to `sign`, `title` or `sfx`, leave speaker and listener empty, and translate it as on-screen text.
- **Register for cổ trang / tiên hiệp** (in `prompts/translator_system.md`, selected by `show.genre_register`):
  - Names, titles, sects, places, cultivation realms, techniques and items use Hán-Việt readings (e.g. 筑基 → Trúc Cơ), recorded in the glossary with the matching `type`.
  - Classical pronoun system: ta / ngươi, huynh / đệ / tỷ / muội, sư phụ / đồ nhi, sư huynh / sư muội, tại hạ, bổn tọa, lão phu, and similar. The pronoun matrix decides which pair applies; the prompt only lists the system.
  - Keep a classical tone but readable subtitle Vietnamese; avoid modern slang and modern pronouns (anh / em, tôi / bạn) unless the matrix says so.
  - Chengyu (成语) are translated by meaning, or by an established Hán-Việt form when one exists; recurring ones go into the glossary as `idiom`.
- **Reviewer corrections:** the memory prefix ends with up to `memory.correction_examples` recent `vi` edits from finished reviews (zh, machine vi → reviewer vi; newest episodes first, deduplicated). The translator applies the same preferences; the evaluator gets the same block (5.12).
- **Retry input:** on a failed evaluation, only the failed lines are resent, with `earlier_attempts` (each earlier translation with its feedback), the `evaluator_suggestion`, and the rest of the window as context. A line that returns an answer it already tried keeps that verdict and is not retried again.
- The prefix actually sent is saved to `work/<episode>/memory_prefix.md` for inspection.

### 5.12 Evaluator (`stages/evaluate.py`)

- **Responsibility:** decide whether each translated line is acceptable.
- **Two layers:**
  1. Rule checks in code, run first (free): line length ≤ `max_line_chars`, lines per event ≤ `max_lines_per_event`, characters per second ≤ `max_cps`, every glossary zh term present in the line has its vi form in the translation, pronoun terms (`translate.pronoun_terms`) used match the matrix for the chosen pair, speaker / listener are known ids (or the episode's new voices), a `confusable` speaker is one of the candidates, a `disputed` speaker is one of the candidates or null.
     - Reading speed (`cps`) is a soft failure unless `translate.retry_on_cps`: it is flagged `cps_exceeded` for review, never retried.
     - Lines with a hard rule failure skip the LLM rubric for that attempt.
  2. LLM rubric (`evaluator` role, different model family, `evaluate.criteria`): meaning, pronouns, register, naturalness, speaker. Scores 1–5; a line fails if any criterion < `evaluate.min_score` or a hard rule check failed. A failing line gets the evaluator's corrected `suggestion`. A line repeating a mistake from the reviewer corrections scores at most 2 on that criterion. A `fixed` / `new_voice` line whose speaker is not the voice's first candidate scores at most 2 on `speaker` unless the dialogue itself shows who speaks (the picture or a guess is no reason; the evaluator sees the translator's `notes`).
- **Loop:** failed lines go back to the translator with feedback, max `translate.max_retries`. After the cap, keep the best attempt (passed, then no rule failures, then total score) and flag `retry_cap` plus the matching rule flags (`line_too_long`, `glossary_mismatch`, `pronoun_mismatch`, `speaker_invalid`, `missing_translation`).
- Other flags set on the final line: `cps_exceeded` (soft), `not_evaluated` (the rubric returned no score), `speaker_override` (translator changed a `fixed` voice speaker), `low_speaker_conf` (`speaker_conf < sprite.trigger_conf_below`).

### 5.13 Sprite check (`stages/sprite.py`, optional)

- **Responsibility:** resolve low-confidence speaker choices between candidates using on-screen art.
- **Trigger:** `sprite.enabled` and flag `low_speaker_conf`.
- **Details:**
  - Extract one full frame at the event midpoint with `ffmpeg -ss <t> -frames:v 1`.
  - For each candidate, run grayscale `cv2.matchTemplate` (TM_CCOEFF_NORMED) with each template at each scale in `sprite.scales`; take the max.
  - Exactly one candidate above `match_threshold` → set that speaker, clear the flag. Otherwise flag `sprite_unresolved` (sent to human review).
  - Log how often it triggers and resolves.

### 5.13a Script review (`stages/script_review.py`)

- **Responsibility:** catch low-value lines the per-line evaluator cannot see, using the whole episode: repeats, OCR noise, unrelated text. Precision first: only lossless merges, the reviewer's own repeated decisions and confident model verdicts remove a line; everything else is flagged.
- **Rules (free):**
  - Identical text back to back with a gap ≤ `repeat_merge_gap_ms` is one subtitle split in two: `remove` (reason `repeat`, `keep_id` = the earlier line, which takes over the removed line's time). The display is unchanged.
  - A similar line (≥ `repeat_similarity`) within `repeat_window_ms` is only flagged.
- **Memory:** a text with at most `memory_max_han` Chinese characters that the reviewer removed ≥ `memory_auto_remove_min` times and never kept is removed (reason `noise`, source `memory`). Counts come from the `line_decisions` table.
- **Model pass:** one call per episode (`script_review.role`, task `script_review`, prompt `prompts/script_review_system.md`) with the whole script (zh, vi, speaker, time) and the reviewer's past decisions (`example_limit` per kind). It returns only lines to remove or check. A removal needs confidence ≥ `remove_confidence`, otherwise it becomes a flag. At most `max_remove_share` of the episode's lines (min 1) are removed; the most confident are kept and the rest become flags.
- **OCR errors in real dialogue** (same call; user decision 2026-10-03): a line that is real dialogue but whose Chinese has an OCR error is not noise. The model returns `action: fix`, `reason: ocr`, the whole corrected line (`zh_fix`) and its context check (`evidence`); the prompt spells out the checks: a 7 becomes 了 only where the particle fits the grammar and a number does not (never deleted, never kept beside an added 了); a character such as 楚 / 姬 / 史 is stray screen text only at the edge of the line, outside its grammar, with the line complete without it, while the same character inside the sentence is the show's wording (euphemism, slang, a name); similar-looking characters and edge doubles only when the context makes the word clear. When it cannot write the corrected line it returns `check` / `ocr`. Code accepts a fix only with evidence, changing at most `fix_max_change_share` of the line, and refuses a 7 that is dropped, kept beside an added 了, or reads as a number (next to a digit, after 第, before one of `measure_words`); a refused fix becomes a `check` flag. Fixes are never applied: the line gets flag `script_ocr` and the editor's notes show the suggested Chinese and the evidence; the reviewer edits the Chinese (pinyin follows) and checks the Vietnamese, which was translated from the wrong text.
- **Measured** (12 human-reviewed episodes, against the OCR answer key, 142 of 1,761 lines with wrong Chinese after OCR correction): the old prompt pointed at 41 of them as noise / suspect, with no fix. The new one suggests 46 fixes, 38 exactly right (83%), 1 harmful (a correct line "fixed"), plus 16 OCR check flags; accepting every fix raises correct Chinese from 1,619 to 1,656 lines. Without the context checks it suggested more (51 right) but damaged 8 correct lines (puns and euphemisms such as 鸡道, 史). It removed 37 lines the reviewer also deleted and 2 the reviewer retyped (garbage readings of 不好 and 也太……). About $0.005 per episode.
- **Output:** `script_review.jsonl` (`ScriptDecision`). The review draft applies it (5.14): removed lines arrive deleted (restorable) with flag `script_<reason>`; flagged lines get `script_suspect`, fixes `script_ocr`, and the note is shown in the editor. In auto mode removed lines are left out of the video; fixes are only listed.
- **Its memory:** after each finished review, the Memory Manager counts per normalized text what the reviewer removed and kept (`record_line_decisions`). Lossless repeat merges are not the reviewer's decision; short lines kept and pre-deleted lines restored count as kept. Locked rows (edited in the Memory screen) are not changed. Each episode's share is kept in `line_decision_episodes`, so finishing a review again replaces that episode's share instead of adding to it.

### 5.14 Review gate and review data (`stages/review.py`)

- **Draft:** one `ReviewedLine` per event, built from events, translations and pinyin, `approved=false`, flags merged from all stages. Two kinds of lines arrive already deleted (restorable):
  - noisy OCR fragments: `ocr_fragment` and at most `review.noise_max_han` Chinese characters or stray digits (`review.predelete_fragments`);
  - the script review's removals (5.13a).
- **Auto mode:** all lines become `approved.jsonl` (deleted ones stay deleted and are not rendered), `edits.jsonl` is empty; flagged lines are listed in `report.md`.
- **Human mode:** the stage writes `review_draft.jsonl`, sets the episode status to `awaiting_review`, and the pipeline stops. The gate reruns only when its inputs changed or it is forced, so an unchanged episode keeps work in progress.
- Review happens in the desktop app (6.4), which only edits `review_draft.jsonl` (autosaved, atomic writes).
- **Finish review:** `finish_review(episode_id)`, called by the app or by `python -m subagent finish-review EPISODE`:
  - Validate, skipping deleted lines: every line approved, speaker/listener ids exist (memory characters, the episode's new voices, NPCs created in review with this episode's number, or candidates whose probation window includes this episode), no empty `vi`.
  - Write `approved.jsonl` and `edits.jsonl` (per changed field, including `deleted`: before, after, event id), compared with the pipeline's original draft.
  - Continue with memory update and render.
- Review never calls an LLM. Pinyin for an edited `zh` is regenerated locally with pypinyin; polyphones in that line get the flag `check_pinyin` instead of an LLM call.

### 5.15 Memory Manager (`memory/manager.py`)

- **Responsibility:** the only component allowed to write memory. Everything else reads through `memory/store.py` read functions.
- **Interface:** `apply(proposals: list[MemoryProposal]) -> ApplyResult`, `update_briefings(episode_id, approved_lines)`, `commit(message)`, `history(limit)`, `diff(commit_sha)`, `entry_history(table, key)`, `rollback(commit_sha)`.
- **Write rules:**
  - A locked entry is changed only by a proposal with `source="human"`.
  - Proposals from `translator` are applied only if their evidence lines were approved.
  - Human edits create or update entries with `locked=1`.
  - A proposal that conflicts with an existing unlocked entry is applied only if it has more evidence than the current entry (`memory_log.evidence_count`); otherwise it is written to `data/memory/conflicts.json` / `conflicts.md` for review.
  - Only human edits delete entries. Deleting a character also deletes its pronoun pairs, voice and confusable pairs.
  - Identical proposals (same kind, source, payload) are merged and their evidence pooled. Characters are applied before the entries that reference them.
  - Every write runs in a transaction and adds a `memory_log` row. Rejected proposals are logged as `op="rejected"` with a reason.
  - An unnamed automatic character (auto id, `name_vi` still equal to the id) takes the first name proposed for it, without the evidence comparison; the id is then replaced by the name in every `briefings/*.md`. Later renames follow the normal rules; a name set by a person is locked.
- **After each episode:**
  - Probation (5.15b, `memory.probation`): candidates that came back are promoted, this episode's new voices and new translator-named characters become candidates, proposals about candidates wait, expired candidates are dropped. With probation off: new voices that approved lines still use (as speaker or listener) become characters at once (`name_zh` = `name_vi` = id, unlocked, source `translator`).
  - Apply approved proposals and human-edit proposals.
  - Record the reviewer's remove / keep decisions in `line_decisions` (5.13a).
  - One `utility` call writes `briefings/<episode_id>.md`, updates `story_so_far.md` within its word cap, and appends to `INDEX.md`. The same call returns `character_fates`: only fates the script states explicitly (`dies`, `leaves`, `returns`) with the stating line as evidence.
  - Character lifecycle (5.15a): record appearances, then update statuses. The commit message counts the moves (`episode ep006: 12 writes, 1 archived`).
  - `git add -A && git commit -m "episode <id>: <n> writes"` in `data/memory/`, then fill `commit_sha` on the new `memory_log` rows.
- **Manual edits from the app:** go through `apply()` with `source="human"`, become locked, and are committed as one commit per save (`manual edit: <n> changes`).
- **Rollback:** `rollback(sha)` closes all DB connections, restores the folder with `git checkout <sha> -- .`, and commits `rollback to <sha>`. History is never rewritten (no `reset --hard`), so a rollback can itself be undone. Refused while any job is running.
- **Locking:** memory writes take `data/memory/.lock` so the app and a running job never write at the same time.
- **All or nothing:** the episode update snapshots the memory files first and restores them if any step fails (NFR-R4).

### 5.15a Character lifecycle (`memory/manager.py: update_lifecycle`)

- **Why:** the show has many come-and-go characters (230+ episodes; a new fish every few episodes) and reuses AI voices between them. Without a lifecycle the character list, prompts and voice bank keep growing, and old one-offs' voices claim new characters.
- **Appearances:** after each episode, every character used as speaker or listener in an approved, non-deleted line gets an `appearances` row (rerun-safe). The first run backfills earlier episodes from their `approved.jsonl`.
- **Generic characters** (`characters.generic`, set only by a person: Memory → Characters "Generic" checkbox): one name for many individuals (e.g. all fish, passers-by). Lines can be assigned to them and they keep their pronoun pairs, but they are left out of voice matching, voice learning, picture matching and sprite learning (`MemoryStore.unmatchable_ids`, with archived characters), never archived by the lifecycle, and marked "(generic: …)" in the prompt's characters block.
- **Rules** (`memory.character_lifecycle`; unlocked characters only: automatic `npc_…` ones and translator-created ones; locked characters are never changed):
  - stated `dies` / `leaves` → `archived`, even if kept;
  - stated `returns` → `kept`;
  - appears in two consecutive episodes (by number) → `kept`; kept characters are never archived for absence;
  - `active` and absent for `memory.archive_after_absent` processed episodes after its last appearance → `archived`;
  - an archived character used again in an approved line → `active` (then the rules above apply).
- **Archived means hidden, not deleted:** left out of the characters and pronoun blocks of every prompt and out of voice matching; rows, voice and history stay. Review dropdowns show it marked "(archived)".
- Every change is a `memory_log` row (source `system`, reason = `status_note`) inside the episode's commit, so it can be rolled back. A person can set `status` / `status_note` in Memory → Characters (that locks the character); model proposals cannot set them.
- Until the visual cast check exists, an appearance is only as reliable as the speaker labels: confirmed in human mode, the machine's guess in auto mode.

### 5.15b Probation for new characters (`memory/probation.py`, `memory/manager.py: probation`)

- **Why:** most wrong memory came from characters created on their first, unchecked appearance (ep005's automatic voices). A new character now has to prove itself first (user decision 2026-10-02).
- **Candidate:** after an episode, a new voice of that episode (`npc_<ep>_<n>`) or an id the translator proposes as a new character, with ≥ `memory.probation_min_lines` approved, non-deleted dialogue lines as speaker, becomes a row in `candidates`: its name (from the translator's proposal, if any), its voice (mean of those lines in `voice_embeddings.npz`) and its look (the unrecognised talking sprites on those lines, `candidate_sprites`). Fewer lines: nothing is remembered (the proposal is logged as rejected). Candidates are not characters: not in the Characters list, prompts' characters block, voice bank or sprite bank; voice and sprite learning skip them.
- **Waiting proposals:** pronoun pairs involving a candidate are stored with it (`pending_json`) and applied when it is promoted. A name proposed for a candidate is kept if it has none yet (first name wins).
- **Coming back:** in an episode numbered 1..`memory.probation_window` after its first, the voice stage gives matching lines the candidate's id (5.8). At finish, the candidate's lines in that episode count: approved lines with it as speaker (human mode), only trusted lines in auto mode (`voice_learning.trusted_auto_lines`: voice, translator and first evaluation agree). Each counting line's talking sprite is compared with its look: a recognised known character talking or a different-looking sprite disagrees; a sprite ≥ `cast.match_similarity` like its look agrees; no talking sprite or no look remembered is neutral. Promoted when at least one line counts and disagreements < agreements + neutral lines. In human mode the reviewer's assignment is the evidence: the candidate is promoted even when the picture disagrees (user decision 2026-10-05: the talking-sprite check overruled a reviewer-assigned return, and the NPC fell out of its window), and the look the picture disputes is not copied into the sprite bank (sprite learning relearns it from the reviewed lines). The look check still gates auto mode.
- **Promotion:** a `characters` row (unlocked; name or id), the candidate's voice in `voice_bank` (voice learning refines it), its look in `sprite_bank`, an `appearances` row for the first episode, then the waiting proposals. `memory_log` rows with source `system`; the episode commit counts it (`1 promoted`).
- **Dropped:** a candidate still waiting when an episode numbered beyond its window finishes. Rows stay (status `dropped`), so it can be inspected or rolled back.
- **From review:** an NPC created in review ("New NPC", 6.4) is added to the episode's new voices at finish (`characters.review_voice_ids`); a candidate assigned by hand in a later episode counts as coming back like one the voice stage found.
- Rerunning an episode's finish rebuilds that episode's candidates. With `memory.probation: false` the old behaviour applies (new voices become characters at once).

### 5.16 Human-edit mining (part of Memory Manager import step)

- A changed `speaker`/`listener` → appended to `data/memory/speaker_corrections.jsonl` for dreaming (mining an episode again first drops its earlier entries).
- A `vi` change where a glossary term's translation differs → glossary proposal with `source="human"`.
- Pronoun changes are not parsed in code; dreaming extracts them (5.18).

### 5.17 Memory bootstrap (`memory/bootstrap.py`, runs before episode 1)

- **Inputs:** `config.yaml`, `data/bootstrap/cast.md` (cast list, relationships, synopsis), `data/bootstrap/voices/<char_id>/*.wav` (3–5 clips each), `data/bootstrap/sprites/<char_id>/*.png`, optionally episode 1 events. Clips and sprites can be captured from episode video in the app's bootstrap wizard (6.6).
- **Steps:**
  1. `utility` call drafts characters (Hán-Việt names), initial pronoun pairs from the stated relationships, and seed glossary terms.
  2. Compute voice-bank centroids; compute pairwise centroid similarity; pairs ≥ `voice.confusable_similarity` go to `confusable_pairs`.
  3. Write the seed draft to `data/bootstrap/seed_draft.json`; the app shows it for review and editing (6.6).
  4. On approval, the Memory Manager writes everything with `locked=1` and commits.
- Rerunnable per character: adding a new character's clips later recomputes only that centroid and its pair similarities.

### 5.18 Dreaming (`memory/dreaming.py`, offline)

- **Trigger:** `python -m subagent dream`, run between episodes (manually or by a scheduler).
- **Inputs:** memory (characters, glossary, pronoun matrix, style rules), `edits.jsonl` not yet seen (`dream_state.json`), `speaker_corrections.jsonl`, up to `memory.dream_max_lines` approved lines, glossary terms used inconsistently, and the rejected proposals.
- **Tasks:**
  - Glossary: find same zh with inconsistent vi across approved lines; propose one form.
  - Relationships: detect pronoun usage in approved lines that differs from the matrix; propose updated pairs (with `since_episode`).
  - Briefings: when `story_so_far.md` reaches 90% of its word cap, compress it to 70% (one `utility` call), proposed as a briefing change.
  - Style rules: turn recurring human edits into short style rules with one example each (`add`, `use` for an existing rule, `remove`), keeping at most `memory.style_rules_max`, dropping the least-used.
- **Filters in code** (nothing to decide is never shown):
  - glossary proposals equal (case-insensitive) to the current entry, and duplicates, are dropped;
  - a style rule of the form "Dịch X thành 'Y'" is a term translation: it becomes a glossary proposal;
  - `add` / `use` of a rule that already exists and `remove` of a rule that does not are dropped;
  - proposals matching a rejected one (by signature: glossary zh + vi, pronoun pair + terms, style rule action + text) are dropped and counted (`previously_rejected`); the prompt also lists the last 60 rejections.
- **Output:** proposals with `source="dreaming"` go through the Memory Manager. All proposals are written to `data/memory/dream_proposals.json` and reviewed in the app's dreaming screen (6.8); unlocked ones are preselected for acceptance, ones touching locked entries are preselected for rejection. The CLI option `dream --auto-apply` applies only proposals that touch no locked entry.
- **Rejection memory:** applying in the app records every unchecked proposal in `dream_rejections.json` (signature, description, date) in the same commit (`dream: <n> writes, <m> rejected`). `--auto-apply` skips proposals on locked entries without recording them as rejected. "Forget rejected proposals" in the app clears the list (its own commit).
- Dreaming never writes directly and never deletes locked entries.

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
python -m subagent partial-review EPISODE    # mid-review: learn from approved lines, re-check the remaining (6.4b)
python -m subagent audit sample|report|benchmark|ocr|remap-key [EPISODE...] [--redraw] [--label NAME] [--no-cache] [--existing] [--archive DIR]   # 6.11, 6.11b, 6.11c
python -m subagent baseline freeze NAME [EPISODE...]   # copy finished reviews into a fixed baseline (6.11d)
python -m subagent status [EPISODE] [--json] # stage completion, cost (total and per agent), flag counts
python -m subagent check                     # binaries, fonts, output folder, API keys, missing prices, device
```

- Every command accepts `--progress json` and `--verbose`. With `--progress json`: one JSON object per line on stdout (`stage`, `status`, `done`, `total`, `cost`, `message`, `error_code`). The desktop app uses this.
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

## 6. Desktop app (UI/UX)

The app covers everything: episodes and runs, review, bootstrap, memory and dreaming. The CLI stays fully usable without it.

### 6.1 Architecture

- Separate package `app/` (PySide6). The core package `subagent/` has no Qt imports.
- **Long jobs** (run, render, bootstrap, dream) run as child processes via `QProcess`, calling the CLI with `--progress json`. The UI parses progress lines. A crash or GPU error in a job cannot freeze or kill the app, and cancelling (terminating the process) is safe because stages resume.
- **Short operations** (reading memory, saving the review draft, pinyin for one line, rule checks) run in-process on a `QThreadPool` worker, never on the UI thread.
- **What the app writes:** `review_draft.jsonl`, audit samples and marks (`audit_sample.jsonl`, `audit_marks.jsonl`, 6.11), bootstrap inputs (`cast.md`, clips, sprites, `seed_draft.json`), config and `.env` through the settings screen, and memory only through `MemoryManager`. Nothing else.
- **Refresh:** the app watches `work/<episode>/state.json` with `QFileSystemWatcher` to update statuses.
- **UI preferences** (language, window layout, splitter sizes, shortcuts, last opened line) are stored with `QSettings`, not in `config.yaml`.

### 6.2 Navigation

- Left sidebar: Episodes, Review, Memory, Bootstrap, Dreaming, Audit, Settings. Episodes is the start screen.
- Status bar: running job and stage, running cost vs budget, device in use (GPU / CPU).

### 6.3 Episodes and run screens

- **Episode table:** id, file, stage progress, status (`new`, `running`, `awaiting_review`, `done`, `failed`, `missing`), flag count, cost (`+ ?` when some calls have no price; the tooltip names the models and gives the cost per agent).
- **Add episodes:** Add files (multi-select), Add folder (with an "include subfolders" checkbox), or drag and drop files and folders onto the table. A confirmation dialog lists file → detected episode number (editable), flags duplicates and files without a detected number, and registers nothing until confirmed (5.21).
- **Missing videos:** rows with status `missing` show a Relink button.
- **Order warning:** running an episode while an earlier one is not done shows a warning dialog.
- **Batch:** the table allows selecting several episodes; Run (auto / human review) with more than one selected starts one `batch --rerun` job in episode order after a confirmation listing the episodes to run, the ones that run again (done or waiting for review: drafts replaced), earlier unfinished episodes left out, and what happens on a failure; in auto mode one Overwrite / Keep both / Cancel choice covers every episode whose output exists. The run panel shows the current episode ("episode ep007 (3/12)") and resets the stage bars for each.
- **Actions:** Run (auto / human): always processes the episode again (`run --rerun`, user decision 2026-10-02); for a `done` or `awaiting_review` episode a confirmation lists the results that will be replaced. Resume does only what is missing (a waiting review opens instead). Rerun from stage (with confirmation listing the results that will be discarded), Render, Open output folder (selects the finished video in Explorer), Open report, Clean temporary files.
- **Output conflict:** when the output file already exists, the dialog from 5.22 (Overwrite / Keep both / Cancel) appears before rendering starts.
- **Run panel:** per-stage progress bars (every pipeline stage including Script review, plus memory, voices, render, report, cleanup), live log tail, cost so far vs budget, Cancel. On failure: the error in plain language and the stage to resume from.

### 6.4 Review screen

Three regions:

- **Line list (left):** columns: state (approved / flagged / pending), time, speaker → listener, zh, vi.
  - Order: always chronological (user decision). Flagged lines are found with the flag filter.
  - Filters: flag group (`retry_cap`, `sprite_unresolved`, `low_speaker_conf`, `non_dialogue_suspect`, `script_ocr`, `script_suspect`, `ocr_uncertain`, `check_pinyin`, rule warnings), deleted, speaker, unapproved only. Search across zh and vi.
  - Header counter: flagged remaining (deleted lines excluded), approved / total, deleted.
- **Preview (top right):** mpv player showing the video with the mask applied and the draft subtitles rendered (6.5). Selecting a line seeks to 0.5 s before its start and plays it once. Controls: timeline slider (click or drag), back / forward 5 s, previous / next frame, play / pause, replay line, loop line, speed 0.5× / 1×.
- **Editor (bottom right):**
  - Editable: zh, pinyin (auto-generated; editing it sets `pinyin_overridden`; Regenerate discards the override), vi (Vietnamese input methods work), speaker and listener (dropdowns of known characters and the episode's new voices), line type.
  - **New character…:** creates a character without leaving review (id, Chinese and Vietnamese names, description), saved through the Memory Manager as a human edit (locked), and assigns it to the line's speaker or listener.
  - **Who is this character?** Under the speaker / listener row, a card for the line's speaker: its picture, "first seen epXXX", description, and ▶ playing a voice sample. **Browse characters…** opens every id the line can take (characters, the episode's new voices, NPCs created in review, candidates on probation) with the same card per row; "Use as speaker" / "Use as listener" assigns one (one undo step). Cards come from `subagent/character_card.py`: name and description from memory (or the candidate), first episode from appearances (or the candidate, or the first reviewed episode it speaks in). The sample, most trusted first: the reviewer's choice; the bootstrap voice clips and sprite templates the reviewer curated (`data/bootstrap/voices|sprites/<id>/`); a line the reviewer approved (finished episodes, or approved in the review under way) with that speaker, the longest ≥ `voice.learn_min_ms`, preferring one with a confirmed box (marked talking or named this character by the reviewer in On screen, or recognised as it by the sprite bank; the machine's talking sprite alone is not trusted). Unreviewed lines are never used (user decision 2026-10-04: an unreviewed guess gave the narrator another character's sprite). From a reviewed line a ≤ 4 s WAV clip (`media.extract_clip`) and the box's picture (the analysed frame, else the video frame) are cut once into `cache/character_cards/<id>/`. **Use this line** on the card makes the current line its speaker's sample: its voice, and the box shown as talking in On screen (nobody marked talking: no picture, e.g. a narrator), kept in `data/character_cards/<id>/` (`pin.json`, `sample.wav`, `picture.png`); it changes the card only, memory learns nothing from it. Loaded in workers. Built because a returning NPC was often given a new id when its old one could not be recognised (user decision 2026-10-03).
  - **New NPC:** gives the line's speaker the next free automatic id of the episode (`npc_<ep>_<n>`, after the voice stage's new voices), shown as "(new NPC)"; nothing is written to memory. The reviewer uses the same id on the character's other lines; at finish it is treated like a new voice of the episode and goes on probation (5.15b) when it speaks ≥ `memory.probation_min_lines` approved lines. The speaker / listener dropdowns also offer candidates on probation that may come back in this episode ("on probation since ep005"), so a return the voice stage missed can be assigned by hand.
  - **Original:** under the Chinese field, the original subtitle pixels (the subtitle band of the frame the cast stage used: the line's middle on the `cast.sample_fps` grid, `video.subtitle_band`), unmasked, to check the OCR text. Loaded in a worker (`Services.line_frame`), the last 40 lines cached; shows why when the video is missing. Below it, **OCR read**: what the recognizer read for the line after pre-processing (`Services.line_ocr_crop`: the line's first reading with the line's raw text, from `ocr_crops/`), at its position in the band, grey where nothing was read; after cleanup or without pre-processing it says so.
  - Read-only context: flags with reasons, script review note, evaluator feedback per attempt, glossary terms found in the line with their required vi forms, and the pronoun pair for the chosen speaker → listener.
- **Right side views** (tabs): **Line** (preview player + editor, as above) and **On screen** (5.8b), where the frame the cast stage used fills the player's place and the recognition table the editor's place (same split sizes). The frame shows every character box: green recognised, orange unknown sprite (`u…`), red outline the talking sprite, each labelled with its position and name. Each table row shows the box's recognised name and similarity, a Talking checkbox (one at most; unticking records "nobody on screen talks"), and a "Correct to" dropdown (as recognised / a character / Not a character). On the picture (boxes drawn at screen scale, labels 11 px): drag a box to move it, a corner to resize it, empty space to draw a box around a missed character (blue, row "A1": choose its character; "Remove this box" or Delete removes it). All of it is one editable part of the line (`cast_labels`, `cast_boxes`, `cast_added`, `cast_talking`: autosaved, one undo step per change, edits.jsonl) and teaches the sprite bank at finish review. **On screen checked** (checkbox under the table, Ctrl+K; `cast_checked`, an edit like the others): the reviewer confirms the line's boxes, names and talking mark as they now stand, so a box left alone counts as confirmed rather than unchecked; such lines are the gold for measuring character recognition (user decision 2026-10-04: checked on every line of 5 replay episodes, the other 11 kept for tests and tuning). The picture is the saved analysed frame when present. The action buttons stay below both views.
  - Live rule checks while typing (line length, CPS, glossary terms, pronoun terms), shown as warnings.
- **Actions:**
  - Approve and next; Approve all remaining non-flagged lines (with confirmation); Finish review (enabled when every non-deleted line is approved; validates, then starts memory update, voice learning and render as a job).
  - Delete line / Restore line: a deleted line is not rendered and not used as memory evidence; it stays in the list, greyed out.
  - Reset line: undo every review change to this line (back to the pipeline's version).
  - Discard review…: replace the whole draft with the pipeline's output, after confirmation. Rerunning a stage (6.3) replaces the draft too.
- **No retranslation:** the review screen never calls an LLM. The user edits lines directly.
- **Draft safety:** every change autosaves to `review_draft.jsonl` (debounced 1 s, atomic write). Undo / redo per line. Reopening an episode restores the draft and the last selected line.

Keyboard shortcuts (defaults; configurable in Settings). The whole review is doable without the mouse.

| Action | Shortcut |
|---|---|
| Approve and next | Ctrl+Enter |
| Next / previous line | Ctrl+↓ / Ctrl+↑ |
| Replay line | Ctrl+R |
| Play / pause | Ctrl+Space |
| Toggle loop | Ctrl+L |
| Focus vi field | Ctrl+E |
| Undo / redo | Ctrl+Z / Ctrl+Y |
| Search | Ctrl+F |
| On screen checked (tick / untick) | Ctrl+K |

### 6.4b Partial review (`partial_review.py`, `python -m subagent partial-review EPISODE`)

- **Why:** within one episode the same minor characters come back many times; what the reviewer confirmed in the first scenes should help the rest of the same review.
- **Start:** the review screen's "Partial review…" button (enabled with some lines approved and some remaining) saves the draft synchronously and runs the job (QProcess, `--progress json`). Approved, non-deleted lines are "reviewed"; unapproved ones are "remaining". It can run any number of times.
- **Session-only learning:** nothing is written to memory; the real learning happens once at finish review (no double counting, no half-learned later edits).
  - Sprites: sprite bank + `sprite_learning.plan` over the reviewed lines (their speakers, talking marks, box names, moved/drawn boxes via `apply_review_edits`); every character in the remaining lines is matched again against that session bank (stored descriptions: seconds, no detection rerun).
  - Voices: voice bank (archived left out) + this episode's reviewed lines (≥ `voice.learn_min_ms`; a character not in the bank needs `voice.learn_min_clips` lines, e.g. the episode's `npc_…` voices; a known one is the clip-count-weighted mean with its centroid); remaining lines' audio is matched again (`stages/voice.match_events`) when at least one voice changed; otherwise the pipeline's voice match (`speakers.jsonl`) is used.
- **Suggestions** (`partial_review.suggest`; never for a line whose speaker the reviewer already changed, or non-dialogue):
  - voice sure (`fixed` / `new_voice`): suggest its speaker unless the talking character disagrees ("picture and voice agree" / "voice");
  - voice `confusable`: the talking character, only if it is one of the voice candidates;
  - no usable voice: the talking character alone ("talking on screen").
- **Output** `partial_review.jsonl` (`PartialSuggestion`: per remaining line, the characters on screen now, talking character, voice match, suggested speaker and reason).
- **In the review screen:** each remaining line with a suggestion gets it as its speaker (user decision 2026-10-02), flagged `partial_speaker` + `check_pronouns` (the Vietnamese pronouns may follow the old speaker; no LLM is called); one undo step per line restores speaker and flags. Notes show the suggestion, talking character and voice; the On screen view shows the session names. A later partial review may change a `partial_speaker` line again (it is still the machine's choice); a speaker the reviewer set is never changed. The "Use <name>" button remains for drafts from before this change (flag `partial_suggestion`).

### 6.5 Live preview

- Uses `render.build_ass()` and `render.build_mask_filter()` (5.19), so the preview matches the final burn-in.
- mpv loads the source video with `vf=lavfi=[<mask filter>]` and the draft ASS written to `work/<episode>/preview.ass`, with `sub-fonts-dir` pointing at `fonts/`.
- After an edit, regenerate `preview.ass` (debounced 300 ms) and send mpv `sub-reload`.
- If libmpv cannot load, the review screen still works without the preview and shows how to fix it.

### 6.6 Bootstrap wizard

1. **Calibrate:** show a frame; the user drags a rectangle over the subtitle band; on release it snaps to be symmetric around the frame's vertical centre line (subtitles are centred; the side closer to the centre widens, so nothing selected is lost; top and bottom stay as drawn; `Band.centered`); fractions are saved to config. Below it, **Subtitle style** (5.4a): the learned style (episode, date, polarity, fill, outline, stroke, letter height) or "not learned yet", "Learn subtitle style from this episode" (runs `calibrate EPISODE --style` as a job; replacing a learned style asks first) and "Show style preview" (the episode's `calibration/style.png`, opened when the job ends). (The CLI `calibrate` command stays for headless use.)
2. **Cast and synopsis:** edit `cast.md` in an editor pane, or import a file.
3. **Voice clips:** per character, mark in / out points on an episode timeline in the preview (timeline slider, ±5 s, frame step), or import WAV files. Play each clip back. A counter shows clips per character (3–5 recommended).
4. **Sprites:** per character, pause the preview and drag a rectangle to crop a template; thumbnails list. Shown only when `sprite.enabled`.
5. **Generate seed:** runs the bootstrap job.
6. **Review seed:** editable tables for characters, pronoun pairs and glossary; confusable pairs read-only with similarity scores and clip playback. Approve writes everything as locked.

Steps 3–4 can be reopened later to add a new character.

### 6.7 Memory screen

Tabs:

- **Characters, Glossary:** searchable, sortable tables; inline edit, add, delete; lock toggle; source and last-updated columns. Deleting a locked entry asks for confirmation. Characters also show `status` (active / kept / archived) and its reason; editing them sets the status by hand.
- **Pronoun matrix:** grid of speaker (rows) × listener (columns). Each cell shows `self_term / address_term`; click to edit. Cells with context variants show a count badge.
- **Briefings, Style rules:** Markdown view with an edit mode.
- **Voice bank:** clip counts per character, similarity heatmap highlighting confusable pairs, clip playback, recompute button.
- **Line decisions:** the script reviewer's memory (text, removed, kept, last episode); editable, edited rows become locked.
- **Conflicts:** entries from `conflicts.json`, each with accept / reject.
- **History:** memory commits (date, message, number of changes). Selecting one shows a per-table diff (rows added / changed / removed, from `memory_log`). "Roll back to this version" asks for confirmation and explains that a new commit is created and nothing is lost. Any table row also has a History action (right-click) showing that entry's changes.

All edits go through `MemoryManager.apply(source="human")` and become locked. Editing and rollback are disabled while a job is running.

### 6.8 Dreaming screen

- Run dream as a job.
- Proposals grouped by kind, each showing before / after and its evidence (click to open the line read-only in that episode's review).
- Unlocked proposals are preselected as accepted; proposals touching locked entries are preselected as rejected and highlighted.
- Apply writes the checked ones through the Memory Manager in one commit; unchecked ones are rejected and never proposed again (5.18).
- The header shows how many proposals were left out because they were rejected before. "Forget rejected proposals…" clears that list after confirmation.

### 6.9 Settings screen

- **General:** default review mode, device, budget, sprite check on / off, render encoder and quality, font sizes.
- **Files:** output folder (folder picker; required before the first render), output name suffix, working folder location, automatic cleanup on / off, video extensions, episode-number patterns with a test field that shows the number detected from a sample file name.
- **Advanced:** raw YAML editor, validated against the config model before saving.
- **API keys:** masked fields saved to `.env`; a test-connection button sends one minimal request.
- **Language:** English / Tiếng Việt; applied after restart (the app offers to restart).
- **Theme:** follows the Windows light / dark setting.
- **Shortcuts:** remap review shortcuts.

### 6.11 Audit (`audit.py`, `app/views/audit.py`, `python -m subagent audit sample|report`)

- **Why:** measure accuracy over many episodes (any series) without checking every line; tell whether checking only flagged lines would be enough.
- **Which episodes:** auto-mode ones. Human-reviewed episodes are left out unless `audit.include_human` (their output is the reviewer's corrected script, so auditing them measures the reviewer; their `edits.jsonl` already records every machine error exactly). The Audit screen lists them greyed as "not audited: reviewed by hand".
- **Sample** (per finished episode, reproducible: seeded by the episode id; `audit_sample.jsonl`, `AuditSample`): `audit.sample_size` random lines of the final script (approved, not deleted), split between flagged and unflagged lines in proportion and at least `audit.min_per_stratum` of each when available; "flagged" ignores `audit.ignore_flags` (reading speed says nothing about correctness). Plus up to `audit.max_disagreements` lines where the voice match (`fixed` / `new_voice`) or the talking sprite names someone else than the final speaker; these are reported separately (not random). An existing sample is kept (marks refer to it) unless `--redraw`.
- **Marking:** the Audit screen lists finished episodes (mode, lines, sampled, marked, error rate so far) with "Draw samples", "Audit selected episode" and "Report…". Auditing opens the review screen in audit mode: read-only, only the sampled lines, with the audit bar: ✓ / ✗ / n/a per aspect (speaker, OCR, translation, pronouns), a note, "All correct, next" (Ctrl+Enter), "Next unmarked"; the list's state column shows ✓ / ✗ / · per line. Marks (`AuditMark`; n/a kept apart from unmarked) autosave to `audit_marks.jsonl` (debounced, atomic). Marks change no output and teach no memory.
- **Report** (`_audit/report.md`, `_audit/summary.json` in the working folder): per aspect, the error rate over all lines of the audited episodes, estimated from the random sample stratified by episode and flagged / unflagged and weighted by line counts, with a 95% normal-approximation range (each stratum smoothed so a clean sample still has a range); flagged vs unflagged and disagreement-line error rates (Wilson 95%); per-episode table with mode and error rate. Only audited (by default auto-mode) episodes count.
- **Answers for a test set:** marking Speaker ✗ shows "Who really speaks" (characters and the episode's new voices); the mark keeps `correct_speaker` (`_new` = nobody known: an NPC or a character appearing for the first time, without an id: the right output is a blank speaker, so gold is None), and every mark keeps `speaker_value` (the line's speaker when marked). "Next unmarked" also stops at ✗ lines still missing that answer; the Audit screen shows "n answers missing".
- Series-neutral: nothing depends on the show.

### 6.11b Speaker benchmark (`benchmark.py`, `python -m subagent audit benchmark`, Audit → Benchmark…)

- **Why:** score every later change (code, memory clean-up, prompts) against what was already audited, with no new hand checking.
- **Gold** (`audit.gold_speakers`): audited lines with a speaker verdict: ✓ → `speaker_value` (fallback: the line's current speaker), ✗ → `correct_speaker`; ✗ without an answer and n/a lines are left out (so before answers exist, "the audited output" scores 100% by construction).
- **Run:** for each episode with gold, a sandbox `<work>/_benchmark/<timestamp>-<label>/<episode>/` gets the episode's `events.jsonl` and `video.json` (OCR held fixed) and, for every other episode, `approved.jsonl` / `edits.jsonl` (the translator's reviewer-corrections block must match a real run); then the real stages audio → voice → cast → windows → translate run there with today's code and memory (memory is only read; nothing learned, nothing rendered). The translator's speaker is compared with the gold. Heavy sandbox files (audio, frames, embeddings) are deleted afterwards.
- **Output:** `report.md` / `summary.json` in the run folder: speaker accuracy now (stratified like the audit report) vs the audited output, accuracy on disagreement lines, per-episode counts, and every line whose speaker changed (✓/✗ against the gold); one line per run in `_benchmark/history.jsonl` (label, date, accuracies, cost). The Audit screen's "Benchmark history…" shows the table and the latest report.
- **Cost:** about 3 minutes and $0.03 of translation per 5-minute episode (measured on ep010). Memory already learned from the audited episodes, so compare runs with each other.

### 6.11c OCR benchmark (`ocr_benchmark.py`, `python -m subagent audit ocr`)

- **Why:** compare OCR settings (5.4) on episodes a person reviewed, with no LLM and no new hand checking.
- **Episodes:** finished human-mode episodes. **Answer key:** their approved Chinese, corrected by `<work>/_ocr_benchmark/answer_key.json` (`corrections`: event id → on-screen text; `excluded`: event id → reason). Built 2026-10-02 by checking every line where the approved Chinese and a second OCR reading disagreed (287) against the subtitle image, plus lines both got wrong the same way: the approved Chinese differed from the screen on about 7% of lines (prop characters such as 姬 / 楚 / 史, 7 for 了, missing edge characters, garbled short lines; 14 deliberate fixes of on-screen typos and names are scored against the screen). 110 corrections, 20 excluded. Traditional and simplified variants count as equal (`VARIANTS`); punctuation is ignored.
- **Run:** a sandbox `<work>/_ocr_benchmark/<timestamp>-<label>/` reruns ingest → OCR → events with today's code and config (bands are deleted afterwards; `events_raw.jsonl`, `ocr_raw.jsonl`, `ocr_samples/` are kept). `--existing` scores the OCR already on disk instead (instant).
- **Scores:** each approved line takes the event overlapping it most in time. Line accuracy (exact text), character error rate (a missed line counts all its characters), missed lines, junk events (events overlapping no approved line for half their time). `report.md` lists every wrong line; `summary.json`; one line per run in `_ocr_benchmark/history.jsonl`.
- **Measured** (against the key): today's OCR 86.6% lines / CER 2.71% (12 episodes); detection capped at 960 px 86.3% / 2.58% but 26 lines missed; on ep001, ep006, ep012: today's OCR 81.4% / 3.94%, line crop of the original pixels 87.8% / 2.05%, line crop of the mask 74.1% / 4.59%, isolated 75.0% / 4.68% (binarised glyphs lose strokes: 于→无, 青→四). All 12 episodes (2026-10-03): line crop 88.9% / 1.98% (7 missed); show-tuned mask (stroke ≤ 0.14, fill mean ≥ 238) 89.9% / 1.80%, with `band_frames: 5` 90.1% / 1.75%; generic segmentation (5.4a) with outline level 14 and share 0.5: 82.9% / 2.75% (101 lines cut at the start or end: end letters failed the outline test), with outline level 72 and share 0.4: 89.3% / 1.82%, with `band_frames: 5` 90.0% / 1.73% (5 missed). Show-tuned gains are the same on episodes never looked at while tuning (+3.2 to +3.5 over today's OCR). Largest remaining error for every method: 了 read as 7 (about half of the wrong lines).
- **Symmetric crop** (2026-10-03, 12 episodes, after the band was re-drawn centred and the style re-learned on ep001; the baseline is segmentation without it): lines right 91.9% / CER 1.42% / junk events 312 → with tolerance 0: 93.0% / 1.24% / 150; 0.25: 93.0% / 1.21% / 144; 0.5: 92.8% / 1.27% / 148; 0.75: 92.9% / 1.25% / 151; 1: 92.7% / 1.28% / 144; 7 missed lines in every run. Lines right in the baseline and wrong with it: 16, 7, 7, 2, 4 (edge letters clipped: 比→此, 才 and 一 lost; plus 了 / 7 flips that a different crop width causes either way). Lines fixed: strays at the line's ends (一他们, 老爹一, 楚，, 史) and short lines read as junk before. 0.75 chosen: nearly the best accuracy, fewest broken lines. The baseline's 91.9% vs the earlier 90.0% comes from the new band and style together.
- **End to end** (2026-10-03, 11 episodes, sandbox with today's memory; before = the episodes' old OCR + the old script review, after = generic segmentation with fusion + the Round 3 script review; both through OCR correction, voice, cast, translation and evaluation, script review): Chinese right after OCR correction 90.8% → 93.7% (95.5% with the script review's fixes accepted); lines translated from wrong Chinese 140 → 91; on the 90 lines whose Vietnamese the reviewer rewrote, similarity to the reviewer's text 0.80 → 0.84; speaker on named characters 92.3% both; evaluator first-pass 92.0% → 92.2%; same cost. The new OCR also reads about 35 lines the old one missed or garbled to noise the reviewer deleted (是我赢了 read as 丰音, 号称肿脸仙人咩 as 女): they are absent from the answer key, so key-based scores understate it and count them as junk.

- **Re-mapping the key:** OCR re-runs renumber events (`stages/events.py`). `python -m subagent audit remap-key --archive DIR` moves each correction and exclusion of the key archived in `DIR` (`answer_key.json` + each episode's old `events.jsonl`) to today's event overlapping its old event most in time (`ocr_benchmark.remap_key`), saves it as the current key and lists the ids that found no line.

### 6.11d Baseline (`baseline.py`, `baseline.name`, `python -m subagent baseline freeze`)

- **Why:** a benchmark suite needs gold that later reruns cannot overwrite (user decision 2026-10-03: ep001–ep016 replayed from the bootstrap memory and re-reviewed in episode order, as the baseline for future experiments).
- While `baseline.name` is set, `finish_review` copies the finished episode to `<work>/_baseline/<name>/<episode>/`: `approved.jsonl`, `edits.jsonl`, `events.jsonl`, `events_raw.jsonl`, `ocr_raw.jsonl`, `translations.jsonl`, `evaluations.jsonl`, `speakers.jsonl`, `new_voices.json`, `cast.jsonl`, `script_review.jsonl`, `pinyin.jsonl`, `video.json`, `state.json`; `manifest.json` records per episode the date, the files, the code and memory git commits and a config hash. Finishing again replaces the copy; a failed copy is reported (`baseline_failed`) and never fails the episode. Character recognition gold: the lines with `cast_checked` (On screen checked on every line of 5 of the 16 episodes). `baseline freeze NAME [EPISODE...]` copies finished episodes by hand.

### 6.10 Interface language (i18n)

- Every user-visible string goes through `self.tr()`. Translations live in `app/i18n/app_en.ts` and `app_vi.ts`, compiled to `.qm` and loaded with `QTranslator` at startup.
- Only the UI is translated. Data (zh, pinyin, vi, memory content, logs) is shown as is.
- Pipeline errors carry stable `error_code` values; the app maps codes to translated messages and falls back to the English message.

## 7. Design choices

| Decision | Reason |
|---|---|
| No agent framework | The flow is fixed and small; plain functions are easier to debug, test and cost-control. |
| Translator and evaluator use different model families | Self-evaluation with the same model shares its blind spots. |
| Rule checks before the LLM evaluator | Length, CPS, glossary and pronoun-term checks are free and deterministic. |
| Speaker inference inside the translation call | Avoids a separate LLM call; the translator already has the dialogue context. |
| Voice match on subtitle-timed slices, no diarization | Subtitle events already segment speech. |
| Confusable pairs computed once at bootstrap | Only lines involving those pairs need tie-breaking. |
| Character lifecycle: one-offs archived after absence or a stated death, recurring ones kept | The cast of minor characters grows without bound; archived voices must not claim new characters who share an AI voice. |
| Unmatched voices grouped into automatic characters with neutral ids (`npc_005_01`) | A new character otherwise gets a random known speaker; the id never changes, so naming it later is a single update. |
| New characters wait on probation until they come back within 2 episodes | Characters created on one unchecked appearance polluted memory; a returning voice (with a look that does not contradict it) is much stronger evidence. |
| An automatic character takes the first name proposed for it, in every episode | Names arrive later than voices; one rename fixes all episodes and briefings. |
| Batch runs episodes in order in one process; auto mode stops at a failure | Models load once; memory builds in episode order, so later episodes should not run on a gap. |
| Audit measures on a stratified random sample; disagreement lines counted apart | A few hundred checked lines estimate accuracy within a few points; non-random lines would bias it. |
| Audit marks never change output or memory | Measurement stays independent of what it measures. |
| Audit answers become a speaker benchmark run in a sandbox | Every change can be scored on already-checked lines; no repeated hand review. |
| The OCR benchmark scores against a corrected answer key, not the approved Chinese as is | About 7% of approved lines kept OCR errors (reviewers check the translation, not the Chinese); scoring against them rewarded the old reader's mistakes. |
| Generic characters are never matched or learned by voice / picture | One name over many voices and looks would pull unrelated lines towards it. |
| Partial review learns per session, writes memory only at finish | Mid-review help without double counting or learning from lines the reviewer may still change. |
| Partial review sets the suggested speaker on unapproved lines, flagged and undoable; no retranslation | Saves a click per line in long reviews; the reviewer still approves every line, review stays free of LLM calls, and changed speakers are flagged for a pronoun check. |
| The picture is weak speaker evidence, shown to the translator only where the voice is unsure | Talking-sprite recognition is wrong about as often as the voice on disputed lines (picture-veto benchmark) and made the translator override sure voices. |
| Visual cast: detect each character, recognise against a learned sprite bank, unknown sprites named by talking-line votes | The cast is too large to name by hand; co-occurrence alone cannot separate characters who are always together, the talking sprite can. |
| Corrections from reviewed speakers remove sprite exemplars that named the wrong character | Early wrong names otherwise pull more wrong crops into a character's library. |
| Auto-mode lines teach the voice bank only through a filter and a measured gate | Auto speakers mostly come from voice match itself; unchecked, its mistakes would reinforce themselves. |
| Sprite check is optional and triggered only on low confidence | Reused art makes template matching reliable and cheap; enable only if the measured ambiguity rate justifies it. |
| Deterministic pinyin with LLM fallback for polyphones only | Pinyin must be correct and free; the LLM is used only where the library is known to be weak. |
| Pinyin generated from corrected Chinese, not from the translation | Pinyin is a reading of the source, independent of translation quality. |
| SQLite for structured memory, Markdown for narrative | Exact lookups for names and pronouns; readable, summarizable text for story context. |
| Index file at the top of briefings | Lets the model decide which episode notes to read without loading all of them. |
| Memory Manager is the sole writer; locked entries | Prevents memory pollution from bad translations or bad dreaming passes. |
| Git versioning of memory | Free, auditable rollback. |
| Stable memory prefix per episode | Maximizes provider prefix-cache hits, the largest single cost saving. |
| LLM response disk cache | Reruns during development cost nothing. |
| Desktop app in a separate package from the core | The CLI stays usable and testable; the UI can change without touching the pipeline. |
| App runs jobs as child processes with JSON progress | A crash or GPU error in a job cannot freeze or kill the UI; cancel is safe because stages resume. |
| mpv (libass) for the preview, sharing ASS and mask builders with the renderer | What the user reviews is what gets rendered. |
| No LLM calls from the review screen | Review costs nothing; the user edits directly. |
| Review list always in time order; flags found with a filter | The user reviews in story order; flagged-first ordering broke the flow of a scene. |
| Script review before human review, precision first | Repeats and OCR noise are only visible across the whole script; a wrong removal costs more than a flag. |
| Pre-deleted lines are restorable, never dropped | The reviewer always sees and can undo what the machine removed. |
| Reviewer corrections fed back into translator and evaluator prompts | Manual edits improve the next episode without waiting for dreaming. |
| Dreaming remembers rejections | Rejected proposals never come back, even reworded. |
| Term translations live only in the glossary | The glossary is enforced by rule checks; a style rule is not. |
| Reading speed is flagged, not retried (default) | Retries for CPS cost tokens and usually cut meaning. |
| Outline test before OCR | Subtitles are outlined text; bright backgrounds without an outline are not sent to OCR. |
| Subtitle band and OCR crop symmetric around the frame's centre | Subtitles are centred; a stray beside one end of the line breaks the symmetry and is cut, with half a line of slack so a missed end letter does not cost a real one. |
| Unpriced models tracked as unknown cost, repriced later | A missing price never silently reports $0 as a real cost. |
| Rollback as a new commit, never rewriting history | A rollback can itself be undone. |
| Interface language applied on restart | Simpler and more reliable than retranslating every widget live. |
| Scene windows instead of single lines | Context improves coherence and pronoun choice. |
| All thresholds in config | Tuning on real episodes needs no code changes. |
| Episode number detected from the file name, always confirmed | Memory depends on episode order, so a wrong guess must never be registered silently. |
| Source videos linked, not copied | Videos are large; relink with a fingerprint check covers moved files. |
| Only the finished video in the output folder | Keeps the output folder clean; everything needed to re-render stays in the working folder. |
| Render to a temp file, move on success | A failed or cancelled render never leaves a broken video under the final name. |
| Learning from a finished review is re-finish safe (line decisions, speaker corrections, sprite votes) | Finishing an episode again (after a correction) must replace its contribution, not count it twice. |
| Reviewed NPCs shown with picture, first episode and voice sample | A returning NPC is recognised by sight and sound; an opaque id led to new ids for old characters and mixed voices. |
| Frozen baseline of re-reviewed episodes | Benchmarks score against gold that reruns cannot overwrite. |
| Auto-delete only temporary files | Frees most of the space while keeping the script and edits that dreaming and re-rendering need. |

## 8. Non-functional requirements

### Cost
- NFR-C1: All non-LLM steps run locally with no paid services.
- NFR-C2: Per-episode LLM spend is tracked per call and reported; the run stops before exceeding `budget.max_cost_per_episode`.
- NFR-C3: Prompts follow the caching layout in 5.1; the report shows the cache-hit share of input tokens.
- NFR-C4: Only failed lines are retranslated, never whole windows.

### Performance
- NFR-P1: The target machine has an NVIDIA GPU. OCR (onnxruntime CUDA provider), voice embeddings (torch CUDA) and encoding (NVENC) use it when `device` is `auto` or `cuda`. Every stage must still run correctly on CPU.
- NFR-P1b: One 5–15 minute episode should process end to end, excluding human review and LLM latency, in a few minutes on the GPU machine. Treat this as a target to measure, not a hard limit. Measured: the cast stage takes about 90 s for a 5-minute episode on the RTX 3060.
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
- NFR-S2: `.env`, `data/episodes/`, `work/`, `cache/` are git-ignored.
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

- Implement in stage order. Each stage must have tests and run on a real short clip before starting the next.
- Never write to memory outside `memory/manager.py`.
- `subagent/` must never import `app/` or PySide6.
- The app never writes pipeline artifacts other than those listed in 6.1; it calls core functions or starts CLI jobs.
- Every user-visible UI string goes through `tr()`; never hardcode interface text.
- Never add a dependency, framework or paid service without asking.
- Never hardcode thresholds, model ids, prices or paths; add them to config.
- Keep prompts in `prompts/`; when changing a prompt, keep the static part stable (caching).
- Use Pydantic models from `models.py` for every artifact; do not pass raw dicts between stages.
- Prefer small pure functions; keep I/O at the stage boundary.
- When a design question is not answered by this file, ask instead of guessing.

## 10. Implementation order

1. Project skeleton, config, models, CLI stub, `llm.py` with cache and cost tracking, episode registry (`add`, `relink`).
2. Calibrate command, then ingest + OCR + events (with non-dialogue detection) on a 2-minute clip; tune band and thresholds.
3. OCR correction.
4. Memory store + Memory Manager + bootstrap (without voices).
5. Pinyin.
6. Windows + translator + evaluator loop, then script review.
7. Review gate, review draft and `finish-review` (CLI), memory update, briefings. Use auto mode until the app's review screen exists.
8. Render, output delivery and cleanup.
9. Audio + voice bank + voice match; add speaker candidates to translator input.
10. Sprite check (only if the measured ambiguity rate justifies it).
11. Dreaming.
12. Report and status command.
13. App shell: navigation, settings, i18n scaffolding (English + Vietnamese), job runner with JSON progress.
14. Episodes and run screens.
15. Review screen with live preview.
16. Memory screen with history and rollback.
17. Bootstrap wizard.
18. Dreaming screen.

## 11. Project facts (confirmed by the user)

| Question | Answer | Where it is handled |
|---|---|---|
| Hardware | NVIDIA GPU | 2, NFR-P1, 5.19 |
| OS | Windows | NFR-PT1–PT5, 5.19 |
| Video resolution | Unknown | Read with ffprobe; band as fractions; fonts scaled by height (5.3, 5.19) |
| Subtitle layout | Fixed position, single line | 5.3 calibration, 5.4 |
| Other text in the band | Unknown | 5.5 non-dialogue detection, 5.11 `line_type` |
| Output | Always pinyin + Vietnamese | 5.19 |
| Setting | Historical / fantasy (cổ trang, tiên hiệp) | 5.11 register, glossary types |
| Episode length | 5–15 minutes | Budget set after the first episode's report |
| Interface | Desktop app with video preview, covering everything | 6 |
| Review preview | Live new subtitles on the masked video | 6.5 |
| Memory in the app | View, edit, roll back | 6.7, 5.15 |
| Interface language | Switchable English / Vietnamese | 6.9, 6.10 |
| Review order | Always chronological; flags via filter | 6.4 |
| Retranslate from review | No, manual edits only | 6.4 |
| Adding videos | Single file, multiple files, folder, drag and drop | 5.21, 6.3 |
| Episode number | Detected from file name, user confirms | 5.21 |
| Source videos | Linked, not copied | 5.21 |
| Output location | One default folder set in Settings | 5.22, 6.9 |
| Output contents | Only the finished video | 5.22 |
| Output name | Source name + `_vi` | 5.22 |
| Existing output file | Ask each time | 5.22 |
| Working files | Temporary files auto-deleted when an episode is done | 5.23 |

Still to measure on the first real episode: subtitle band fractions, change and OCR thresholds, voice-match thresholds, non-dialogue thresholds, and per-episode cost.
