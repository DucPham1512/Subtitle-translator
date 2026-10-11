"""Load and validate config.yaml into Pydantic models; resolve project paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from subagent.errors import ConfigError


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShowConfig(_Section):
    name: str = "<show name>"
    genre_register: str = "co_trang_tien_hiep"


class Band(_Section):
    top: float = 0.80
    bottom: float = 0.97
    left: float = 0.05
    right: float = 0.95

    @field_validator("top", "bottom", "left", "right")
    @classmethod
    def _fraction(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("band fractions must be between 0 and 1")
        return v

    def pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) in pixels, rounded to even values for ffmpeg crop."""
        x = int(round(self.left * width)) // 2 * 2
        y = int(round(self.top * height)) // 2 * 2
        w = max(2, int(round((self.right - self.left) * width)) // 2 * 2)
        h = max(2, int(round((self.bottom - self.top) * height)) // 2 * 2)
        w = min(w, width - x)
        h = min(h, height - y)
        return x, y, w, h

    def centered(self) -> Band:
        """Symmetric around the frame's vertical centre line (subtitles are centred): the side closer to the centre
        grows to match the other, so nothing selected is lost; top and bottom are kept."""
        half = max(0.5 - self.left, self.right - 0.5)
        return self.model_copy(update={"left": round(max(0.0, 0.5 - half), 4),
                                       "right": round(min(1.0, 0.5 + half), 4)})


class VideoConfig(_Section):
    sample_fps: float = 4
    subtitle_band: Band = Field(default_factory=Band)
    text_threshold: int = 200
    change_threshold: float = 0.02
    empty_text_ratio: float = 0.002
    # Burned-in subtitles are bright text with a dark outline; snow, sky or white clothes are bright without one.
    subtitle_detection: Literal["outline", "bright"] = "outline"   # "bright": any bright pixels count as text
    outline_dark_threshold: int = 60      # grayscale at or below this is an outline pixel
    outline_reach_px: int = 2             # a bright pixel this close to a dark one is outlined
    min_outlined_ratio: float = 0.006     # band with fewer outlined bright pixels holds no subtitle
    # resolution (5.3): each saved band is the per-pixel median of up to this many sampled frames that show the
    # same subtitle (static text stays sharp, compression noise and moving background average out); 1 = off
    band_frames: int = 1
    stable_range: int = 12                # grey change at most this across a subtitle's frames: a "stable" pixel
    calibrate_fps: float = 2.0            # style calibration (5.4a): sampling rate...
    calibrate_max_bands: int = 400        # ...and at most this many bands from the episode


class OcrConfig(_Section):
    min_confidence: float = 0.6
    merge_max_edit_distance: int = 1
    fragment_max_samples: int = 1            # events on screen for this many sampled frames or fewer are "fragments"
    fragment_merge_similarity: float = 0.6   # fold a fragment into a neighbour this similar (or containing it)
    # engine (RapidOCR); defaults are RapidOCR's own. "min" 736 scales a 48 px band's short side up ~15x.
    det_limit_type: Literal["min", "max"] = "min"
    det_limit_side_len: int = 736
    use_cls: bool = True                     # text-direction classifier (subtitles are never upside down)
    # pre-processing (5.4): none | mask (keep only white strokes ringed by a dark outline, black on white)
    preprocess: Literal["none", "mask", "segment"] = "none"   # segment: the series' calibrated style (5.4a)
    mask_bright: int = 200                   # grayscale at or above this is subtitle fill
    mask_dark: int = 60                      # at or below this is outline
    mask_reach_px: int = 2                   # a fill pixel this close to a dark one is outlined
    mask_min_outline: float = 0.6            # share of a stroke's edge that must be outlined
    mask_max_height: float = 1.0             # stroke components at most this tall (fraction of band height)...
    mask_max_width: float = 1.6              # ...and this wide (in band heights); larger bright areas are scenery
    mask_min_area: int = 4                   # px; smaller specks are noise
    mask_min_mean: int = 0                   # subtitle fill is near pure white: mean grey of a stroke at least this
                                             # (scenery measured <= 234, subtitle >= 241); 0 = off
    mask_max_stroke: float = 0.0             # widest inside of a stroke (distance to its edge) as a share of the
                                             # band height; wider bright areas are surfaces (a cooler), 0 = off
    mask_scale: float = 2.0                  # enlarge the cleaned band before OCR
    mask_pad: int = 8                        # white margin around it (px, after scaling)
    # detect: the detection model finds text boxes | line (needs preprocess: mask): the masked subtitle line
    # is cropped (components grouped by gaps of at most box_max_gap line heights, the largest group kept) and
    # only the recognition model reads it
    recognize: Literal["detect", "line"] = "detect"
    line_min_height: float = 0.4             # a group lower than this share of the band is specks, not a line
    line_crop_vertical: bool = False         # also crop the line top to bottom (letters fill more of the reader)
    # subtitles are centred on the frame: trim the side of the line crop farther from the frame's centre to the
    # other side's length (strays next to one end); a line not spanning the centre is read as nothing
    symmetric_crop: bool = False
    symmetric_crop_tolerance: float = 0.5    # ...leaving this much difference, in line heights (a missed end letter)
    # segment (5.4a): tolerances around the calibrated style (data/bootstrap/subtitle_style.json)
    seg_stroke_tolerance: float = 0.6        # stroke width within this share of the series' stroke width
    seg_outline_share: float = 0.4           # share of a component's surrounding ring that must be outline
                                             # (letters measured 0.56-0.77, scenery <= 0.16 at the calibrated level)
    seg_max_height: float = 1.3              # components at most this many letter heights tall...
    seg_max_width: float = 2.0               # ...and this many letter heights wide (larger: background)
    seg_min_stable: float = 0.6              # share of a component that stayed still (when ingest saved stability)
    # what OCR reads with preprocess: mask: mask (black text on white) | original (the band's own pixels; in
    # line mode cropped to the line) | isolated (own pixels inside the widened text mask, black elsewhere)
    mask_image: Literal["mask", "original", "isolated"] = "mask"
    isolate_grow_px: int = 3                 # how far the text mask is widened to keep the outline (isolated)
    # box filter after OCR (5.4): the subtitle is one line of uniform height; drop boxes beside it
    box_filter: bool = False
    box_min_height: float = 0.7              # boxes shorter than this share of the main box are dropped...
    box_max_gap: float = 1.5                 # ...as are boxes further than this many line heights from it
    sample_images: int = 0                   # save this many before/after band images to ocr_samples/ (temporary)
    save_crops: bool = True                  # save what OCR read per reading to ocr_crops/ for the review screen


class NonDialogueConfig(_Section):
    enabled: bool = True
    box_height_tolerance: float = 0.25
    box_center_tolerance: float = 0.15
    max_duration_ms: int = 8000


class OcrFixConfig(_Section):
    batch_size: int = 50
    max_char_changes: int = 2


class AudioConfig(_Section):
    sample_rate: int = 16000
    pad_ms: int = 100
    min_event_ms: int = 400


class VoiceConfig(_Section):
    model: str = "speechbrain/spkrec-ecapa-voxceleb"
    top_k: int = 3
    accept_score: float = 0.55
    min_margin: float = 0.08
    unknown_below: float = 0.35
    confusable_similarity: float = 0.75
    learn_from_reviews: bool = True       # rebuild the voice bank from reviewed lines after each finish-review
    learn_min_ms: int = 800               # reviewed lines shorter than this carry too little voice
    learn_trim_ms: int = 80               # cut from both ends of a line (neighbouring speech bleeds in)
    learn_min_clips: int = 3              # a character needs this many samples to get a voice
    learn_outlier_share: float = 0.1      # least typical share of samples dropped (likely mislabelled lines)
    learn_from_auto: bool = True          # auto-mode episodes may teach too, through the filter and gate below
    learn_auto_min_score: float = 0.70    # voice match top-1 score (status "fixed" or "new_voice")
    learn_auto_min_margin: float = 0.15   # top-1 minus top-2
    learn_auto_allowed_flags: list[str] = Field(default_factory=lambda: ["cps_exceeded", "check_pinyin"])
    learn_auto_min_test_lines: int = 30   # human-reviewed lines needed to measure whether auto lines help
    learn_auto_max_drop: float = 0.0      # accuracy on human-reviewed lines may not drop more than this
    new_voices: bool = True               # group voices that match no known character into new characters
    new_voice_below: float = 0.55         # lines whose best known-character score is below this may be new
    new_voice_similarity: float = 0.60    # lines are grouped when their voices are at least this similar
    new_voice_known_max: float = 0.55     # a group whose average voice scores this high is a known character
    new_voice_min_lines: int = 3          # smaller groups stay unknown
    new_voice_prefix: str = "npc"         # ids look like npc_005_01 (episode 5, voice 1)

    @field_validator("new_voice_prefix")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum() or not v.isascii() or v != v.lower():
            raise ValueError("new_voice_prefix must be lowercase ascii letters, digits or _")
        return v


class CastConfig(_Section):
    """Who is on screen during each line, and who is talking (5.8b)."""
    enabled: bool = True
    detector_model: str = "google/owlv2-base-patch16-ensemble"
    embed_model: str = "facebook/dinov2-base"
    queries: list[str] = Field(default_factory=lambda: ["a cartoon character", "a cartoon person", "a cartoon fish",
                                                        "a dog"])
    frame_width: int = 960                 # frames are scaled to this width for detection
    sample_fps: float = 5                  # decoding rate when picking each line's middle frame
    min_score: float = 0.15                # detector confidence
    min_box_height: float = 0.12           # fractions of the frame
    min_box_width: float = 0.05
    max_box_width: float = 0.9
    nms_iou: float = 0.5
    match_similarity: float = 0.70         # a crop this close to a library exemplar of one character is that character
    match_margin: float = 0.03             # ...and this much closer than to any other character
    unknown_similarity: float = 0.75       # unrecognised crops this similar are the same unknown sprite (per episode)
    motion_fps: float = 10                 # talking detection: frames per second over the line
    motion_width: int = 480
    talk_dominance: float = 1.6            # the talking sprite moves this many times more than any other
    learn: bool = True                     # learn the sprite bank from finished episodes
    name_min_votes: int = 3                # an unknown sprite needs this many talking-line votes for one speaker
    name_min_share: float = 0.75           # ...and this share of its votes
    add_similarity: float = 0.85           # a recognition this sure joins the library (new poses)
    max_exemplars: int = 60                # per character, the best-confirmed are kept


class PinyinConfig(_Section):
    polyphone_fallback: bool = True
    polyphones: list[str] = Field(default_factory=lambda: ["了", "行", "长", "得", "还"])


class WindowsConfig(_Section):
    gap_ms: int = 3000
    max_lines: int = 40
    context_overlap: int = 5


class TranslateConfig(_Section):
    max_retries: int = 2
    max_line_chars: int = 42
    max_lines_per_event: int = 2
    max_cps: float = 17
    retry_on_cps: bool = False               # False: reading speed is flagged for review, never retried
    # the talking character on screen can dispute the voice match (5.11): off | recognised (a recognised
    # different character talks) | any (also an unrecognised one)
    picture_veto: Literal["off", "recognised", "any"] = "off"
    # what the translator sees of the picture (5.11): all lines | tiebreak (only lines whose voice is not sure:
    # confusable / unknown / too_short / disputed) | off
    picture_evidence: Literal["all", "tiebreak", "off"] = "tiebreak"
    pronoun_terms: list[str] = Field(default_factory=list)


class EvaluateConfig(_Section):
    min_score: int = 3
    criteria: list[str] = Field(
        default_factory=lambda: ["meaning", "pronouns", "register", "naturalness", "speaker"]
    )


class SpriteConfig(_Section):
    enabled: bool = True
    match_threshold: float = 0.8
    scales: list[float] = Field(default_factory=lambda: [0.6, 0.8, 1.0, 1.2])
    trigger_conf_below: float = 0.6


class ScriptReviewConfig(_Section):
    enabled: bool = True
    role: Literal["utility", "evaluator", "translator"] = "utility"   # one call per episode
    repeat_merge_gap_ms: int = 300        # identical text with at most this gap: one subtitle, merged
    repeat_window_ms: int = 4000          # a similar line within this time is flagged as a possible repeat
    repeat_similarity: float = 0.6
    remove_confidence: float = 0.9        # the model removes a line only this sure; otherwise it is flagged
    max_remove_share: float = 0.1         # safety cap: more removals than this share become flags
    example_limit: int = 30               # reviewer decisions shown to the model, per kind
    memory_auto_remove_min: int = 2       # a short text you removed this often and never kept is removed
    memory_max_han: int = 2               # "short": at most this many Chinese characters
    fix_max_change_share: float = 0.5     # an OCR fix may change at most this share of the line's characters
                                          # (more is a rewrite, not a correction); at least ocr_fix.max_char_changes
    # a 7 the model turns into 了 is kept a number (the fix becomes a flag) when it touches another digit, follows
    # 第, or is followed by one of these measure words / units
    measure_words: str = "斤个天年月日号块元万千百米分秒点岁次条只位名人层倍级度两寸里"


class AuditConfig(_Section):
    sample_size: int = 20                 # random lines per audited episode
    min_per_stratum: int = 3              # at least this many flagged and unflagged lines (when available)
    max_disagreements: int = 15           # extra lines where voice / picture / speaker disagree
    include_human: bool = False           # human-reviewed episodes measure the reviewer, not the system
    # flags that say nothing about correctness (reading speed): ignored when splitting flagged / unflagged
    ignore_flags: list[str] = Field(default_factory=lambda: ["cps_exceeded", "check_pinyin"])


class ReviewConfig(_Section):
    mode: Literal["human", "auto"] = "human"
    predelete_fragments: bool = True         # noisy one-frame OCR fragments arrive in review already deleted
    noise_max_han: int = 2                   # ...when they have at most this many Chinese characters or stray digits


class MemoryConfig(_Section):
    story_so_far_max_words: int = 600
    style_rules_max: int = 30
    dream_max_lines: int = 400
    correction_examples: int = 20            # recent reviewer corrections shown to translator and evaluator
    character_lifecycle: bool = True         # keep / archive unlocked characters by their appearances (5.15a)
    archive_after_absent: int = 2            # archive an unlocked one-off character after this many episodes away
    # probation (5.15b): a new character becomes one only when it comes back
    probation: bool = True
    probation_min_lines: int = 3             # approved lines it speaks in its first episode to become a candidate
    probation_window: int = 2                # it must come back within this many episodes (by number)
    # character updates (5.15c): one utility call per finished episode updates names, descriptions, aliases, pronouns
    character_updates: bool = False
    description_max_chars: int = 200         # a description the model writes is cut to this length
    aliases_max: int = 8                     # aliases kept per character


class RenderConfig(_Section):
    font_dir: str = "fonts"
    font_name: str = "Noto Sans"
    pinyin_font_size: float = 36
    vi_font_size: float = 48
    pinyin_min_scale: float = 0.7
    line_spacing: float = 1.2
    avg_char_width: float = 0.55
    outline: float = 2.5
    shadow: float = 0
    primary_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    mask: Literal["blur", "box"] = "blur"
    blur_radius: int = 20
    mask_color: str = "black"
    encoder: Literal["auto", "h264_nvenc", "libx264"] = "auto"
    quality: int = 20


class ProviderConfig(_Section):
    base_url: str
    api_key_env: str
    model: str


class PriceConfig(_Section):
    input: float = 0.0
    input_cached: float = 0.0
    output: float = 0.0


class LlmConfig(_Section):
    temperature: float = 0
    max_retries: int = 5
    timeout_s: float = 120
    max_retry_wait_s: float = 90           # longest wait before a retry, also when the provider asks for more
    providers: dict[Literal["translator", "evaluator", "utility"], ProviderConfig]
    prices: dict[str, PriceConfig] = Field(default_factory=dict)


class BudgetConfig(_Section):
    max_cost_per_episode: float = 1.0


class PathsConfig(_Section):
    work_dir: str = "work"


class EpisodesConfig(_Section):
    video_extensions: list[str] = Field(
        default_factory=lambda: [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".ts"]
    )
    number_patterns: list[str] = Field(default_factory=lambda: [r"(\d{1,4})"])


class OutputConfig(_Section):
    folder: str | None = None
    name_suffix: str = "_vi"
    on_exists: Literal["ask", "overwrite", "keep_both", "fail"] = "ask"


class CleanupConfig(_Section):
    auto: bool = True


class BaselineConfig(_Section):
    # while set, every finished review is copied to <work>/_baseline/<name>/<episode>/ (gold + machine output +
    # the memory version), so later reruns cannot overwrite the data a benchmark is built on
    name: str | None = None


class SeriesConfig(_Section):
    # the series to work on (data/series/<slug>/, with its own series.yaml overrides); null: the single-series
    # layout directly under data/. load_config sets it to the active series (--series, $SUBAGENT_SERIES)
    default: str | None = None


class BenchConfig(_Section):
    # the frozen baseline the benchmark suite scores against (6.11e); null: the one baseline.name freezes into
    baseline: str | None = None


class Config(_Section):
    show: ShowConfig = Field(default_factory=ShowConfig)
    device: Literal["auto", "cuda", "cpu"] = "auto"
    video: VideoConfig = Field(default_factory=VideoConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    non_dialogue: NonDialogueConfig = Field(default_factory=NonDialogueConfig)
    ocr_fix: OcrFixConfig = Field(default_factory=OcrFixConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    cast: CastConfig = Field(default_factory=CastConfig)
    pinyin: PinyinConfig = Field(default_factory=PinyinConfig)
    windows: WindowsConfig = Field(default_factory=WindowsConfig)
    translate: TranslateConfig = Field(default_factory=TranslateConfig)
    evaluate: EvaluateConfig = Field(default_factory=EvaluateConfig)
    sprite: SpriteConfig = Field(default_factory=SpriteConfig)
    script_review: ScriptReviewConfig = Field(default_factory=ScriptReviewConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    llm: LlmConfig
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    episodes: EpisodesConfig = Field(default_factory=EpisodesConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    baseline: BaselineConfig = Field(default_factory=BaselineConfig)
    bench: BenchConfig = Field(default_factory=BenchConfig)
    series: SeriesConfig = Field(default_factory=SeriesConfig)

    def section(self, name: str) -> dict:
        """JSON-able dump of one top-level section (used in stage input hashes)."""
        value = getattr(self, name)
        return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


SERIES_DIR = "series"           # data/series/<slug>/
SERIES_FILE = "series.yaml"     # a series' overrides of config.yaml sections
# config.yaml sections that describe one show: `series migrate` moves them to series.yaml, and settings saved for
# them while a series is active are written there
SERIES_SECTIONS = ("show", "video", "ocr", "non_dialogue", "voice", "cast", "script_review", "paths", "baseline",
                   "bench")


def series_root(root: Path) -> Path:
    return root / "data" / SERIES_DIR


def list_series(root: Path) -> list[str]:
    folder = series_root(root)
    return sorted(p.name for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []


class Paths:
    """All project locations, derived from the project root and config.

    Shared by every series: config.yaml, .env, prompts/ (general prompts), cache/. Per series (data/series/<slug>/,
    or data/ itself in the single-series layout): memory/, bootstrap/, episodes/index.json, character_cards/,
    fonts/ (subtitle font, `render.font_dir` relative to the series folder), prompts/ (series notes), and the work
    folder (`paths.work_dir`)."""

    def __init__(self, root: Path, config: Config | None = None):
        self.root = root.resolve()
        self.series = config.series.default if config else None
        work = Path(config.paths.work_dir) if config else Path("work")
        self.work = work if work.is_absolute() else self.root / work
        self.config_file = self.root / "config.yaml"
        self.env_file = self.root / ".env"
        self.prompts = self.root / "prompts"
        self.data = series_root(self.root) / self.series if self.series else self.root / "data"
        self.series_file = self.data / SERIES_FILE if self.series else None
        self.series_prompts = self.data / "prompts"
        self.episodes_index = self.data / "episodes" / "index.json"
        self.bootstrap = self.data / "bootstrap"
        self.memory = self.data / "memory"
        self.memory_db = self.memory / "memory.db"
        self.card_pins = self.data / "character_cards"
        self.cache = self.root / "cache"
        self.llm_cache = self.cache / "llm"
        self.models_cache = self.cache / "models"
        self.card_cache = self.cache / "character_cards" / self.series if self.series else \
            self.cache / "character_cards"
        font_dir = Path(config.render.font_dir) if config else Path("fonts")
        self.fonts = font_dir if font_dir.is_absolute() else (self.data if self.series else self.root) / font_dir

    def episode_dir(self, episode_id: str) -> Path:
        return self.work / episode_id


def find_root(start: Path | None = None) -> Path:
    """Project root: $SUBAGENT_ROOT, else the nearest folder (upwards) holding config.yaml."""
    env = os.environ.get("SUBAGENT_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "config.yaml").is_file():
            return candidate
    return here


def parse_config(data: dict) -> Config:
    try:
        return Config.model_validate(data or {})
    except ValidationError as exc:
        raise ConfigError(f"config.yaml is invalid:\n{exc}") from exc


def merge_sections(base: dict, override: dict) -> dict:
    """Deep merge: nested mappings are merged key by key, any other value (lists included) replaces."""
    out = dict(base)
    for key, value in (override or {}).items():
        out[key] = merge_sections(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) \
            else value
    return out


def _read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name} is not valid YAML: {exc}") from exc


def active_series(root: Path, data: dict, series: str | None = None) -> str | None:
    return series or os.environ.get("SUBAGENT_SERIES") or (data.get("series") or {}).get("default")


def series_data(root: Path, data: dict, series: str | None) -> dict:
    """config.yaml's data with the active series' series.yaml merged in. The series is `series`, else
    $SUBAGENT_SERIES, else `series.default`; none: the single-series layout. A series without its own
    `paths.work_dir` works in <work_dir>/<slug>/."""
    slug = active_series(root, data, series)
    if not slug:
        return data
    folder = series_root(root) / slug
    if not folder.is_dir():
        known = ", ".join(list_series(root)) or "none yet"
        raise ConfigError(f"series '{slug}' not found in {series_root(root)} (series: {known})")
    own = _read_yaml(folder / SERIES_FILE) if (folder / SERIES_FILE).is_file() else {}
    merged = merge_sections(data, own)
    if not (own.get("paths") or {}).get("work_dir"):
        base = Path((data.get("paths") or {}).get("work_dir") or "work")
        merged = merge_sections(merged, {"paths": {"work_dir": str(base / slug)}})
    return merge_sections(merged, {"series": {"default": slug}})


def load_config(root: Path | None = None, series: str | None = None) -> tuple[Config, Paths]:
    root = root or find_root()
    path = root / "config.yaml"
    if not path.is_file():
        raise ConfigError(f"config.yaml not found in {root}")
    data = _read_yaml(path)
    config = parse_config(series_data(root, data, series))
    _load_env(root / ".env")
    return config, Paths(root, config)


def _load_env(env_file: Path) -> None:
    if env_file.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False, encoding="utf-8")


def save_config_text(root: Path, text: str, *, series_file: bool = False, series: str | None = None) -> Config:
    """Validate raw YAML, then write it atomically: config.yaml, or with `series_file` the active series'
    series.yaml. Validation uses the merged result (config.yaml + the active series' overrides)."""
    from subagent.util import atomic_write_text

    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Not valid YAML: {exc}") from exc
    shared = _read_yaml(root / "config.yaml")
    slug = active_series(root, shared, series)
    if series_file:
        if not slug:
            raise ConfigError("no series is active: there is no series.yaml to save")
        target = series_root(root) / slug / SERIES_FILE
        config = parse_config(merge_sections(series_data(root, shared, slug), data))
    else:
        target = root / "config.yaml"
        config = parse_config(series_data(root, data, slug) if active_series(root, data, series) else data)
    atomic_write_text(target, text)
    return config


def update_config_values(root: Path, updates: dict[str, object], series: str | None = None) -> Config:
    """Set dotted keys (e.g. "video.subtitle_band"), validate the merged result and save. With a series active,
    a key whose section is a series section (`SERIES_SECTIONS`) or already in its series.yaml is written there,
    any other key in config.yaml. Comments are not preserved for rewritten files; the raw editor keeps them."""
    from subagent.util import atomic_write_text

    shared = _read_yaml(root / "config.yaml")
    slug = active_series(root, shared, series)
    own_path = series_root(root) / slug / SERIES_FILE if slug else None
    own = _read_yaml(own_path) if own_path and own_path.is_file() else {}
    touched = {"shared": False, "series": False}
    for dotted, value in updates.items():
        keys = dotted.split(".")
        to_series = bool(slug) and (keys[0] in SERIES_SECTIONS or keys[0] in own)
        node = own if to_series else shared
        touched["series" if to_series else "shared"] = True
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
    config = parse_config(merge_sections(series_data(root, shared, slug), own) if slug else shared)
    if touched["shared"]:
        atomic_write_text(root / "config.yaml", yaml.safe_dump(shared, allow_unicode=True, sort_keys=False))
    if touched["series"] and own_path is not None:
        atomic_write_text(own_path, f"# series '{slug}': overrides of config.yaml sections for this show\n"
                          + yaml.safe_dump(own, allow_unicode=True, sort_keys=False))
    return config
