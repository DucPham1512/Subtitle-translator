"""Stage 6b: who is on screen during each line, and who is talking (5.8b).

For each subtitle event the middle frame goes through an open-vocabulary detector (OWLv2: "a cartoon
character", ...) and every character found is described by an image model (DINOv2). A description close to
one character's exemplars in the sprite bank names it; the others become per-episode unknown sprites. Over the
line's duration, movement inside each character's head area is measured with the camera's pan/zoom cancelled:
in this show the talking sprite is the one that moves (face swaps, bobbing). The sprite bank itself is learned
after each finished episode (memory/sprite_learning.py).
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from subagent.config import CastConfig, Config, Paths
from subagent.context import EpisodeContext
from subagent.errors import ModelUnavailableError
from subagent.memory.store import MemoryStore
from subagent.models import CastDetection, CastLine, SubtitleEvent
from subagent.util import read_jsonl, write_jsonl

log = logging.getLogger(__name__)

_ENGINE: CastEngine | None = None
Bank = dict[str, tuple[np.ndarray, list[int]]]          # character -> (exemplars k x d, exemplar ids)


# -- models ----------------------------------------------------------------------------------------

class CastEngine:
    """OWLv2 finds characters, DINOv2 describes each one. Loaded once per process; GPU when available."""

    def __init__(self, config: Config, paths: Paths):
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel, Owlv2ForObjectDetection, Owlv2Processor
        except ImportError as exc:
            raise ModelUnavailableError(
                "Cast recognition needs transformers + torch: pip install -e \".[cast]\" (see README)") from exc
        from transformers.utils import logging as hf_logging

        from subagent.device import torch_device

        hf_logging.disable_progress_bar()       # progress output is ours (--progress json)
        self.cfg = config.cast
        self.cache = str(paths.models_cache / "hf")
        self._torch = torch
        self._owl = (Owlv2Processor, Owlv2ForObjectDetection)
        self._dino = (AutoImageProcessor, AutoModel)
        self.device = torch_device(config)
        self.queries = list(self.cfg.queries)
        self.det = self.emb = None            # each model loads on first use (learning only needs the image model)

    def _detector(self):
        if self.det is None:
            proc, model = self._owl
            self.det_proc = proc.from_pretrained(self.cfg.detector_model, cache_dir=self.cache)
            self.det = model.from_pretrained(self.cfg.detector_model, cache_dir=self.cache).to(self.device).eval()
            log.info("cast: %s loaded on %s", self.cfg.detector_model, self.device)
        return self.det

    def _embedder(self):
        if self.emb is None:
            proc, model = self._dino
            self.emb_proc = proc.from_pretrained(self.cfg.embed_model, cache_dir=self.cache)
            self.emb = model.from_pretrained(self.cfg.embed_model, cache_dir=self.cache).to(self.device).eval()
            log.info("cast: %s loaded on %s", self.cfg.embed_model, self.device)
        return self.emb

    def detect(self, frame: np.ndarray, threshold: float) -> list[tuple[list[float], float, str]]:
        """(box x0,y0,x1,y1 in frame pixels, score, query) for an RGB frame."""
        h, w = frame.shape[:2]
        det = self._detector()
        inputs = self.det_proc(text=[self.queries], images=frame, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            out = det(**inputs)
        side = max(w, h)   # OWLv2 pads to a square: boxes are relative to the padded side
        res = self.det_proc.post_process_grounded_object_detection(out, threshold=threshold,
                                                                   target_sizes=[(side, side)])[0]
        boxes = res["boxes"].cpu().numpy()
        return [([float(np.clip(b[0], 0, w)), float(np.clip(b[1], 0, h)), float(np.clip(b[2], 0, w)),
                  float(np.clip(b[3], 0, h))], float(s), self.queries[int(lab)])
                for b, s, lab in zip(boxes, res["scores"].cpu().numpy(), res["labels"].cpu().numpy(), strict=True)]

    def embed(self, crops: list[np.ndarray]) -> np.ndarray:
        """L2-normalized image features, one row per RGB crop."""
        if not crops:
            return np.zeros((0, 0), np.float32)
        emb = self._embedder()
        inputs = self.emb_proc(images=crops, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            feats = emb(**inputs).pooler_output
        return self._torch.nn.functional.normalize(feats, dim=-1).cpu().numpy().astype(np.float32)


def get_engine(config: Config, paths: Paths) -> CastEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = CastEngine(config, paths)
    return _ENGINE


NOT_A_CHARACTER = "_none"       # reviewer label for a box that is not a character
FRAMES_DIR = "cast_frames"      # the exact frames the stage analysed (temporary: review + learning use them)


def frame_path(work: Path, event_id: str) -> Path:
    return work / FRAMES_DIR / f"{event_id.replace(':', '_')}.jpg"


def load_frame(work: Path, event_id: str) -> np.ndarray | None:
    """The saved analysed frame (RGB), or None when it was cleaned up or never saved."""
    path = frame_path(work, event_id)
    if not path.is_file():
        return None
    data = np.fromfile(str(path), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return None if img is None else img[:, :, ::-1].copy()


def save_frame(work: Path, event_id: str, rgb: np.ndarray) -> None:
    path = frame_path(work, event_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", rgb[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])
    if ok:
        tmp = path.with_suffix(".tmp")
        buf.tofile(str(tmp))
        tmp.replace(path)


def crop(frame: np.ndarray, box: list[float]) -> np.ndarray:
    h, w = frame.shape[:2]
    x0, y0 = int(max(0, min(box[0], box[2]))), int(max(0, min(box[1], box[3])))
    x1, y1 = int(min(w, max(box[0], box[2]))), int(min(h, max(box[1], box[3])))
    return frame[y0:max(y1, y0 + 1), x0:max(x1, x0 + 1)]


def frame_time_ms(event: SubtitleEvent, sample_fps: float) -> int:
    """The time of the frame the stage used for an event: its middle, on the `sample_fps` decoding grid."""
    mid = (event.start_ms + event.end_ms) / 2000
    return int(round(round(mid * sample_fps) / sample_fps * 1000))


# -- pure helpers ----------------------------------------------------------------------------------

def keep_boxes(dets: list[tuple[list[float], float, str]], cfg: CastConfig, w: int, h: int) -> list[int]:
    """Size filter, then non-maximum suppression (also dropping a box mostly inside a kept one: a head in a body)."""
    cand = [i for i, (b, s, _) in enumerate(dets) if s >= cfg.min_score and (b[3] - b[1]) >= cfg.min_box_height * h
            and cfg.min_box_width * w <= (b[2] - b[0]) <= cfg.max_box_width * w]
    cand.sort(key=lambda i: -dets[i][1])
    keep: list[int] = []
    for i in cand:
        bi = dets[i][0]
        ok = True
        for j in keep:
            bj = dets[j][0]
            ix = max(0.0, min(bi[2], bj[2]) - max(bi[0], bj[0]))
            iy = max(0.0, min(bi[3], bj[3]) - max(bi[1], bj[1]))
            inter = ix * iy
            ai = (bi[2] - bi[0]) * (bi[3] - bi[1])
            aj = (bj[2] - bj[0]) * (bj[3] - bj[1])
            if inter / (ai + aj - inter + 1e-6) >= cfg.nms_iou or inter / (ai + 1e-6) >= 0.8:
                ok = False
                break
        if ok:
            keep.append(i)
    return keep


def build_bank(store: MemoryStore, without: set[int] | None = None) -> Bank:
    """Sprite bank by character, leaving out archived characters (their art can be reused for new ones) and the
    exemplar ids in `without` (those an episode about to be learned again added last time)."""
    skip = store.unmatchable_ids()
    rows: dict[str, list] = {}
    for ex in store.sprite_exemplars():
        if ex.character_id not in skip and ex.id not in (without or set()):
            rows.setdefault(ex.character_id, []).append(ex)
    return {c: (np.stack([e.embedding for e in exs]), [e.id for e in exs]) for c, exs in rows.items()}


def match(emb: np.ndarray, bank: Bank, cfg: CastConfig) -> tuple[str | None, float, int | None]:
    """(character, similarity, exemplar id) when one character's closest exemplar is close enough and clearly
    closer than any other character's; else (None, best similarity, None)."""
    best: list[tuple[float, str, int]] = []
    for char, (mat, ids) in bank.items():
        sims = mat @ emb
        k = int(np.argmax(sims))
        best.append((float(sims[k]), char, ids[k]))
    best.sort(reverse=True)
    if best and best[0][0] >= cfg.match_similarity and (len(best) == 1 or best[0][0] - best[1][0] >= cfg.match_margin):
        return best[0][1], best[0][0], best[0][2]
    return None, (best[0][0] if best else 0.0), None


def group_unknowns(embs: list[np.ndarray], similarity: float) -> list[int]:
    """Greedy per-episode grouping: each crop joins the most similar earlier group (by its closest member) when
    at least `similarity`, else starts a group. Returns a group number per crop."""
    groups: list[list[np.ndarray]] = []
    out = []
    for e in embs:
        best, gid = -1.0, -1
        for g, members in enumerate(groups):
            s = float(np.max(np.stack(members) @ e))
            if s > best:
                best, gid = s, g
        if gid >= 0 and best >= similarity:
            groups[gid].append(e)
            out.append(gid)
        else:
            groups.append([e])
            out.append(len(groups) - 1)
    return out


def talking_index(motions: list[float | None], dominance: float) -> int | None:
    """The detection that moves clearly more than every other one; None when none clearly does or only one
    character is on screen (a lone character may be listening to someone off screen)."""
    m = sorted(((v, i) for i, v in enumerate(motions) if v is not None), reverse=True)
    if len(m) < 2:
        return None
    return m[0][1] if m[0][0] >= dominance * max(m[1][0], 0.5) else None


# -- video -----------------------------------------------------------------------------------------

def _ffmpeg() -> str:
    from subagent.media import require_binary

    return require_binary("ffmpeg")


def middle_frames(video: Path, times: list[float], w: int, h: int, fps: float) -> dict[float, np.ndarray]:
    """Decode once at `fps` and keep the RGB frame nearest to each wanted time (seconds)."""
    proc = subprocess.Popen([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(video), "-vf",
                             f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    want = sorted(set(times))
    out: dict[float, np.ndarray] = {}
    size = w * h * 3
    i = k = 0
    try:
        while k < len(want):
            buf = proc.stdout.read(size) if proc.stdout else b""
            if len(buf) < size:
                break
            t = i / fps
            while k < len(want) and want[k] <= t + 0.5 / fps:
                out[want[k]] = np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
                k += 1
            i += 1
    finally:
        proc.kill()
        proc.wait()
    return out


def _residual(prev: np.ndarray, cur: np.ndarray, band_top: int) -> np.ndarray | None:
    """|cur - prev moved by the dominant (camera) motion|; NaN where undefined or in the subtitle area."""
    pts = cv2.goodFeaturesToTrack(prev, 400, 0.01, 6)
    if pts is None or len(pts) < 12:
        return None
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, pts, None)
    good = st.ravel() == 1
    if good.sum() < 12:
        return None
    m, _ = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if m is None:
        return None
    h, w = prev.shape
    warped = cv2.warpAffine(prev, m, (w, h), flags=cv2.INTER_LINEAR)
    valid = cv2.warpAffine(np.ones_like(prev), m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    d = cv2.absdiff(cv2.GaussianBlur(cur, (5, 5), 0), cv2.GaussianBlur(warped, (5, 5), 0)).astype(np.float32)
    d[valid == 0] = np.nan
    d[band_top:] = np.nan
    return d


def line_motion(video: Path, start_ms: int, end_ms: int, boxes: list[list[float]], scale: float, h: int,
                cfg: CastConfig, band_top_fraction: float) -> list[float | None]:
    """Mean camera-compensated movement in the upper half (head) of each box over the line.
    `boxes` are in detection-frame pixels; the motion frames are `scale` times that size (cfg.motion_width x h)."""
    w = cfg.motion_width
    proc = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{start_ms / 1000:.3f}",
                           "-i", str(video), "-t", f"{max(0.1, (end_ms - start_ms) / 1000):.3f}", "-vf",
                           f"fps={cfg.motion_fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                          capture_output=True)
    data = np.frombuffer(proc.stdout, np.uint8)
    frames = data[: (data.size // (w * h)) * w * h].reshape(-1, h, w)
    return motion_in_boxes(frames, boxes, scale, band_top_fraction)


def motion_in_boxes(frames: np.ndarray, boxes: list[list[float]], scale: float,
                    band_top_fraction: float) -> list[float | None]:
    if len(frames) < 3:
        return [None] * len(boxes)
    h, w = frames.shape[1:]
    band_top = int(band_top_fraction * h)
    acc = np.zeros((h, w), np.float64)
    cnt = np.zeros((h, w), np.float64)
    for a, b in zip(frames[:-1], frames[1:], strict=True):
        d = _residual(a, b, band_top)
        if d is None:
            continue
        ok = ~np.isnan(d)
        acc[ok] += d[ok]
        cnt[ok] += 1
    mean = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    out: list[float | None] = []
    for box in boxes:
        x0, y0, x1, y1 = (v * scale for v in box)
        x0, x1 = int(max(0, x0)), int(min(w, x1))
        y0, y1 = int(max(0, y0)), int(min(band_top, y1))
        if x1 - x0 < 4 or y1 - y0 < 4:
            out.append(None)
            continue
        head = mean[y0:y0 + max(2, (y1 - y0) // 2), x0:x1]
        out.append(float(np.nanmean(head)) if np.isfinite(head).any() else None)
    return out


# -- stage -----------------------------------------------------------------------------------------

MotionFn = Callable[[SubtitleEvent, list[list[float]]], list[float | None]]
FramesFn = Callable[[list[float], int, int], dict[float, np.ndarray]]


def run(ctx: EpisodeContext, engine: CastEngine | None = None, motion_fn: MotionFn | None = None,
        frames_fn: FramesFn | None = None) -> dict[str, int]:
    cfg = ctx.config.cast
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    if not cfg.enabled or not events:
        write_jsonl(ctx.artifact("cast.jsonl"), [])
        np.save(ctx.artifact("cast_embeddings.npy"), np.zeros((0, 0), np.float32))
        return {"lines": 0}
    video = ctx.require_source()
    info = ctx.video_info()
    w = cfg.frame_width
    h = int(round(w * info.height / info.width / 2)) * 2
    engine = engine or get_engine(ctx.config, ctx.paths)
    bank = build_bank(MemoryStore(ctx.paths.memory_db))
    band_top = ctx.config.video.subtitle_band.top
    scale = cfg.motion_width / w
    motion_h = int(round(cfg.motion_width * info.height / info.width / 2)) * 2
    if motion_fn is None:
        def motion_fn(e: SubtitleEvent, boxes: list[list[float]]) -> list[float | None]:
            return line_motion(video, e.start_ms, e.end_ms, boxes, scale, motion_h, cfg, band_top)

    mids = {e.id: (e.start_ms + e.end_ms) / 2000 for e in events}
    frames = (frames_fn or (lambda ts, fw, fh: middle_frames(video, ts, fw, fh, cfg.sample_fps)))(
        list(mids.values()), w, h)
    lines: list[CastLine] = []
    embs: list[np.ndarray] = []
    unknown_rows: list[tuple[int, int]] = []          # (line position, detection position)
    for n, e in enumerate(events, 1):
        frame = frames.get(mids[e.id])
        line = CastLine(event_id=e.id)
        if frame is not None:
            save_frame(ctx.work, e.id, frame)
            dets = engine.detect(frame, min(0.1, cfg.min_score))
            keep = keep_boxes(dets, cfg, w, h)
            crops = [crop(frame, dets[i][0]) for i in keep]
            feats = engine.embed(crops) if crops else np.zeros((0, 0), np.float32)
            for k, i in enumerate(keep):
                box, score, label = dets[i]
                char, sim, _ = match(feats[k], bank, cfg)
                line.detections.append(CastDetection(index=len(embs), box=[round(v, 1) for v in box],
                                                     score=round(score, 3), label=label, character=char,
                                                     similarity=round(sim, 4)))
                embs.append(feats[k])
                if char is None:
                    unknown_rows.append((len(lines), len(line.detections) - 1))
            if len(line.detections) >= 2:
                motions = motion_fn(e, [d.box for d in line.detections])
                for d, mv in zip(line.detections, motions, strict=True):
                    d.motion = None if mv is None else round(mv, 3)
                line.talking = talking_index([d.motion for d in line.detections], cfg.talk_dominance)
        lines.append(line)
        ctx.progress.emit("cast", "progress", done=n, total=len(events))
    groups = group_unknowns([embs[lines[li].detections[di].index] for li, di in unknown_rows], cfg.unknown_similarity)
    for (li, di), g in zip(unknown_rows, groups, strict=True):
        lines[li].detections[di].unknown = f"u{g + 1:03d}"
    write_jsonl(ctx.artifact("cast.jsonl"), lines)
    np.save(ctx.artifact("cast_embeddings.npy"), np.stack(embs) if embs else np.zeros((0, 0), np.float32))
    talkers = [ln.talker() for ln in lines if ln.talking is not None]
    return {
        "lines": len(lines),
        "characters": len(embs),
        "recognised": sum(d.character is not None for ln in lines for d in ln.detections),
        "unknown_sprites": len(set(groups)),
        "talking": len(talkers),
        "talking_recognised": sum(t.character is not None for t in talkers if t),
    }
