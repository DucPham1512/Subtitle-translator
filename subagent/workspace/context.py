"""Per-episode context handed to every stage: config, paths, artifacts, LLM client, progress."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from subagent.kernel.models import Episode, VideoInfo
from subagent.kernel.progress import NULL_PROGRESS, Progress
from subagent.llm.client import LLMClient
from subagent.settings.config import Config, Paths
from subagent.workspace.episodes import Registry


@dataclass
class EpisodeContext:
    config: Config
    paths: Paths
    episode: Episode
    registry: Registry | None = None
    progress: Progress = NULL_PROGRESS
    use_cache: bool = True
    llm_override: LLMClient | None = None
    _llm: LLMClient | None = field(default=None, init=False, repr=False)
    _video: VideoInfo | None = field(default=None, init=False, repr=False)

    @property
    def work(self) -> Path:
        return self.paths.episode_dir(self.episode.id)

    def artifact(self, name: str) -> Path:
        return self.work / name

    @property
    def source(self) -> Path:
        return Path(self.episode.source_path)

    def require_source(self) -> Path:
        """Check the video still exists before a stage reads it (5.21)."""
        if self.registry is not None:
            self.episode = self.registry.check_source(self.episode.id)
        elif not self.source.is_file():
            from subagent.kernel.errors import SourceMissingError

            raise SourceMissingError(f"The video for {self.episode.id} is missing: {self.source}")
        return self.source

    @property
    def llm(self) -> LLMClient:
        if self.llm_override is not None:
            return self.llm_override
        if self._llm is None:
            self._llm = LLMClient(
                self.config, self.paths, cost_path=self.artifact("cost.jsonl"), use_cache=self.use_cache,
                on_cost=self.progress.set_cost,
            )
        return self._llm

    def video_info(self) -> VideoInfo:
        """Probe info saved by ingest (video.json); probes the source when missing."""
        if self._video is None:
            path = self.artifact("video.json")
            if path.is_file():
                self._video = VideoInfo.model_validate_json(path.read_text(encoding="utf-8"))
            else:
                from subagent.infra.media import probe

                self._video = probe(self.require_source())
        return self._video
