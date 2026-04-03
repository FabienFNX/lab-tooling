"""Session configuration and metadata models."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.services.recorder.util import get_iso_timestamp, get_package_versions, get_python_version


class SessionConfig(BaseModel):
    """Configuration for a recording session."""

    session_id: str
    name: str
    out_dir: Path
    samplerate: int = Field(default=48000, gt=0)
    channels_mic: int = Field(default=1, gt=0)
    channels_system: int = Field(default=2, gt=0)
    blocksize: int = Field(default=2048, gt=0)
    mic_device: str | None = None
    speaker_device: str | None = None
    record_source: str = Field(default="both")
    output_format: str = Field(default="wav")
    display_mode: str = Field(default="minimal")
    mixdown: bool = False
    mic_gain: float = Field(default=1.0, gt=0)
    sys_gain: float = Field(default=1.0, gt=0)

    class Config:
        arbitrary_types_allowed = True


class FileInfo(BaseModel):
    """Information about a recorded file."""

    path: str
    size_bytes: int


class SessionResult(BaseModel):
    """Result metadata for a completed recording session."""

    session_id: str
    name: str
    started_at: str
    ended_at: str
    duration_seconds: float

    samplerate: int
    blocksize: int
    channels_mic: int
    channels_system: int
    record_source: str
    output_format: str
    display_mode: str

    mic_device: str | None = None
    speaker_device: str | None = None

    mic_file: FileInfo | None = None
    system_file: FileInfo | None = None
    mix_file: FileInfo | None = None

    frames_recorded_mic: int
    frames_recorded_system: int
    dropped_mic_blocks: int = 0
    dropped_sys_blocks: int = 0

    python_version: str
    package_versions: dict[str, str]

    @classmethod
    def create(
        cls,
        config: SessionConfig,
        started_at: str,
        duration: float,
        frames_mic: int,
        frames_sys: int,
        dropped_mic: int,
        dropped_sys: int,
        mic_path: Path | None,
        sys_path: Path | None,
        mix_path: Path | None = None,
    ) -> "SessionResult":
        def file_info(path: Path | None) -> FileInfo | None:
            if not path:
                return None
            return FileInfo(path=str(path), size_bytes=path.stat().st_size if path.exists() else 0)

        mic_device = None
        speaker_device = None
        if config.record_source in ("both", "mic"):
            mic_device = config.mic_device or "default"
        if config.record_source in ("both", "system"):
            speaker_device = config.speaker_device or "default"

        return cls(
            session_id=config.session_id,
            name=config.name,
            started_at=started_at,
            ended_at=get_iso_timestamp(),
            duration_seconds=duration,
            samplerate=config.samplerate,
            blocksize=config.blocksize,
            channels_mic=config.channels_mic,
            channels_system=config.channels_system,
            record_source=config.record_source,
            output_format=config.output_format,
            display_mode=config.display_mode,
            mic_device=mic_device,
            speaker_device=speaker_device,
            mic_file=file_info(mic_path),
            system_file=file_info(sys_path),
            mix_file=file_info(mix_path) if mix_path else None,
            frames_recorded_mic=frames_mic,
            frames_recorded_system=frames_sys,
            dropped_mic_blocks=dropped_mic,
            dropped_sys_blocks=dropped_sys,
            python_version=get_python_version(),
            package_versions=get_package_versions(),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
