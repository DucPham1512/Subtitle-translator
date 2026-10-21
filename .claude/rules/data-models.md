---
paths:
  - "subagent/kernel/models.py"
  - "subagent/memory/**"
---
## 4. Data models

Defined in `subagent/kernel/models.py`. All JSONL artifacts are one serialized model per line.

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
    source: Literal["translator", "human", "bootstrap", "dreaming", "updater"]   # updater: character updates (5.15c)
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

Other models in `kernel/models.py`: `VideoInfo`, `ChangeRecord`, `OcrBox`, `OcrReading`, `PinyinLine`, `Window`, `StageState`, `EpisodeState`, `CastBoxEdit` (5.8b), `PartialSuggestion` (6.4b), `AuditSample` / `AuditMark` (6.11; aspects `AUDIT_ASPECTS` = speaker, ocr, translation, pronouns; `AuditMark.na` lists aspects marked not applicable).

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
  generic INTEGER NOT NULL DEFAULT 0,      -- many individuals under one name (all fish, passers-by)
  aliases TEXT NOT NULL DEFAULT '[]'       -- JSON list of titles / other names, "会长 (Hội trưởng)" (5.15c)
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
  updated_at TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]'         -- JSON list (5.15c), moved to the character on promotion
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
- `character_updates.json`: character updates waiting for the reviewer (locked entries, untrusted auto-mode lines; 5.15c).
- `character_update_rejections.json`: character updates the reviewer rejected; never held again (5.15c).
