"""Shared Pydantic data models. Every JSONL artifact is one serialized model per line."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EpisodeStatus = Literal["new", "running", "awaiting_review", "done", "failed", "missing"]
LineType = Literal["dialogue", "sign", "title", "sfx"]
SpeakerStatus = Literal["fixed", "confusable", "unknown", "too_short", "new_voice", "disputed"]
ProposalKind = Literal["glossary", "pronoun_pair", "character", "style_rule", "briefing", "line_decision"]
ProposalSource = Literal["translator", "human", "bootstrap", "dreaming"]


class Episode(BaseModel):
    id: str                    # "ep003", from the confirmed episode number (zero-padded to 3)
    number: int
    source_path: str           # absolute path; the video is never copied
    source_size: int
    source_mtime: float
    source_fingerprint: str    # SHA-256 of size + first 1 MB + last 1 MB
    added_at: str
    status: EpisodeStatus = "new"
    output_path: str | None = None


class VideoInfo(BaseModel):
    width: int
    height: int
    duration_ms: int
    fps: float
    has_audio: bool
    audio_codec: str | None = None
    video_codec: str | None = None


class ChangeRecord(BaseModel):
    t_ms: int
    kind: Literal["text", "empty"]


class OcrBox(BaseModel):
    """One detected text box; coordinates are fractions of the band size."""

    text: str
    confidence: float
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def vcenter(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def hcenter(self) -> float:
        return (self.x0 + self.x1) / 2


class OcrReading(BaseModel):
    t_ms: int
    kind: Literal["text", "empty"]
    text: str = ""
    confidence: float = 0.0
    boxes: list[OcrBox] = Field(default_factory=list)
    multi_row: bool = False
    low_conf: bool = False
    # geometry of the whole reading (fractions of band size), used for non-dialogue detection
    box_height: float | None = None
    box_vcenter: float | None = None
    box_hcenter: float | None = None


class SubtitleEvent(BaseModel):
    id: str                    # "<episode_id>:<index:04d>"
    start_ms: int
    end_ms: int
    zh_raw: str                # OCR output, merged across frames
    zh: str                    # after OCR correction
    ocr_conf: float            # mean OCR confidence
    ocr_fixed: bool = False
    flags: list[str] = Field(default_factory=list)   # non_dialogue_suspect, ocr_uncertain, ocr_low_conf
    notes: list[str] = Field(default_factory=list)   # reasons behind flags, OCR fix reasons
    box_height: float | None = None
    box_vcenter: float | None = None
    box_hcenter: float | None = None
    multi_row: bool = False

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def suspect(self) -> bool:
        return "non_dialogue_suspect" in self.flags


class SpeakerCandidates(BaseModel):
    event_id: str
    candidates: list[tuple[str, float]] = Field(default_factory=list)   # (character_id, cosine), top-k, sorted
    status: SpeakerStatus


class NewVoice(BaseModel):
    """A group of lines that sound alike but match no known character (`new_voices.json`)."""
    id: str                            # npc_005_01
    event_ids: list[str]
    cohesion: float                    # mean similarity of the lines to their average voice
    closest_known: str | None = None   # the known character the average voice is closest to
    closest_score: float = 0.0
    returning_from: str | None = None  # a candidate (5.15b) first heard in that episode, heard again here
    name_vi: str | None = None         # the candidate's name, when the dialogue gave one


class CastDetection(BaseModel):
    """One character found in a line's middle frame (cast.jsonl)."""
    index: int                         # row in cast_embeddings.npy
    box: list[float]                   # x0, y0, x1, y1 in the detection frame (cast.frame_width wide)
    score: float
    label: str                         # the detector query that found it
    character: str | None = None       # recognised from the sprite bank
    similarity: float = 0.0            # to the closest exemplar
    unknown: str | None = None         # per-episode unknown sprite id ("u001") when not recognised
    motion: float | None = None        # movement inside the head area with camera pan/zoom cancelled


class CastBoxEdit(BaseModel):
    """A box the reviewer drew around a character the detector missed."""
    box: list[float]                   # x0, y0, x1, y1 in the cast frame (cast.frame_width wide)
    character: str | None = None


class CastLine(BaseModel):
    event_id: str
    detections: list[CastDetection] = Field(default_factory=list)
    talking: int | None = None         # position in `detections` of the clearly talking sprite

    def on_screen(self) -> list[str]:
        return sorted({d.character for d in self.detections if d.character})

    def talker(self) -> CastDetection | None:
        return self.detections[self.talking] if self.talking is not None else None


class PartialSuggestion(BaseModel):
    """Partial review (partial_review.jsonl): one remaining line re-checked mid-review."""
    event_id: str
    cast: dict[str, str | None] = Field(default_factory=dict)       # detection position -> character now
    similarity: dict[str, float] = Field(default_factory=dict)
    talking: str | None = None                                      # the talking sprite's character now
    voice: SpeakerCandidates | None = None                          # voice match with this episode's voices
    suggested_speaker: str | None = None
    reason: str = ""


AUDIT_ASPECTS = ("speaker", "ocr", "translation", "pronouns")


class AuditSample(BaseModel):
    """One sampled line of an audited episode (audit_sample.jsonl)."""
    event_id: str
    kind: Literal["random", "disagreement"]
    flagged: bool
    disagreement: list[str] = Field(default_factory=list)   # e.g. "voice: npc_005_02"


class AuditMark(BaseModel):
    """The auditor's verdict on one line (audit_marks.jsonl): True correct, False wrong, None not applicable."""
    event_id: str
    speaker: bool | None = None
    ocr: bool | None = None
    translation: bool | None = None
    pronouns: bool | None = None
    na: list[str] = Field(default_factory=list)    # aspects marked "not applicable" (e.g. no pronoun in the line)
    correct_speaker: str | None = None             # when speaker is wrong: who really speaks (benchmark gold)
    speaker_value: str | None = None               # the line's speaker when it was marked
    note: str = ""
    marked_at: str = ""

    def marked(self) -> bool:
        return any(getattr(self, a) is not None for a in AUDIT_ASPECTS) or bool(self.na) or bool(self.note)

    def any_wrong(self) -> bool:
        return any(getattr(self, a) is False for a in AUDIT_ASPECTS)


class PinyinLine(BaseModel):
    event_id: str
    pinyin: str
    flags: list[str] = Field(default_factory=list)


class ScriptDecision(BaseModel):
    """Whole-script review verdict on one line (script_review.jsonl)."""

    event_id: str
    action: Literal["remove", "flag"]
    reason: Literal["repeat", "noise", "unrelated", "other"]
    source: Literal["rule", "memory", "llm"]
    confidence: float = 1.0
    note: str = ""
    keep_id: str | None = None   # repeats: the line that stays (a merged one takes over the removed line's time)


class Window(BaseModel):
    index: int
    event_ids: list[str]
    context_ids: list[str] = Field(default_factory=list)   # previous lines, read-only context


class MemoryProposal(BaseModel):
    kind: ProposalKind
    payload: dict
    source: ProposalSource
    evidence: list[str] = Field(default_factory=list)      # event ids or edit ids


class LineTranslation(BaseModel):
    event_id: str
    speaker: str | None
    listener: str | None
    speaker_conf: float        # 0..1, from translator
    line_type: LineType = "dialogue"
    vi: str
    attempts: int
    flags: list[str] = Field(default_factory=list)   # retry_cap, low_speaker_conf, sprite_unresolved, cps_exceeded
    proposals: list[MemoryProposal] = Field(default_factory=list)
    notes: str = ""


class Evaluation(BaseModel):
    event_id: str
    attempt: int
    passed: bool
    scores: dict[str, int] = Field(default_factory=dict)   # criterion -> 1..5
    feedback: str = ""
    rule_failures: list[str] = Field(default_factory=list)     # hard failures: the line is retried
    soft_failures: list[str] = Field(default_factory=list)     # flagged for review only (e.g. reading speed)
    suggestion: str = ""                                       # evaluator's corrected line when it failed


class ReviewedLine(BaseModel):
    event_id: str
    start_ms: int
    end_ms: int
    speaker: str | None
    listener: str | None
    zh: str
    pinyin: str
    vi: str
    line_type: LineType = "dialogue"
    pinyin_overridden: bool = False
    approved: bool = False
    edited: bool = False
    flags: list[str] = Field(default_factory=list)
    deleted: bool = False      # removed in review: not rendered, not used as memory evidence
    # reviewer's corrections of the cast boxes (5.8b): detection position (as str) -> character id or "_none"
    cast_labels: dict[str, str] = Field(default_factory=dict)
    cast_boxes: dict[str, list[float]] = Field(default_factory=dict)   # moved/resized detected boxes, by position
    cast_added: list[CastBoxEdit] = Field(default_factory=list)        # boxes drawn around missed characters
    cast_talking: str | None = None    # reviewer's talking sprite: position, "a<i>" (drawn box) or "none"


class EditRecord(BaseModel):
    edit_id: str               # "<event_id>:<field>"
    event_id: str
    field: str
    before: str | None
    after: str | None


class CostRecord(BaseModel):
    ts: str
    role: str
    model: str
    prompt_tokens: int = 0
    cache_hit_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    cached_response: bool = False   # served from the local disk cache
    task: str = ""                  # the agent that made the call (translate, evaluate, script_review, ...)
    # False: no price was configured when the call was made; the cost is computed from the tokens once a
    # price exists (see llm.record_cost). None: written before this field existed.
    priced: bool | None = None


class StageState(BaseModel):
    status: Literal["done", "purged", "failed", "running"] = "done"
    input_hash: str = ""
    output_hash: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    duration_s: float = 0.0
    counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class EpisodeState(BaseModel):
    episode_id: str
    mode: Literal["human", "auto"] | None = None
    stages: dict[str, StageState] = Field(default_factory=dict)
    purged: list[str] = Field(default_factory=list)
