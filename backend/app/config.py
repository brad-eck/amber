"""Configuration loading and defaults for Amber.

Reads config.toml from the data directory. Creates a default config file
on first run if none exists.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

# Project root is two levels up from this file (backend/app/config.py -> amber/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class StorageConfig:
    data_path: str = "./data"

    @property
    def resolved_data_path(self) -> Path:
        """Resolve data_path relative to the project root."""
        p = Path(self.data_path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p


@dataclass
class TranscriptionConfig:
    whisper_model: str = "base"
    language: str = "en"


@dataclass
class RecordingConfig:
    max_duration_seconds: int = 300
    video_codec: str = "h264"
    container: str = "mp4"


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class AmberConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def _config_to_dict(cfg: AmberConfig) -> dict:
    """Serialize config to a plain dict suitable for TOML output."""
    return {
        "storage": {"data_path": cfg.storage.data_path},
        "transcription": {
            "whisper_model": cfg.transcription.whisper_model,
            "language": cfg.transcription.language,
        },
        "recording": {
            "max_duration_seconds": cfg.recording.max_duration_seconds,
            "video_codec": cfg.recording.video_codec,
            "container": cfg.recording.container,
        },
        "server": {
            "host": cfg.server.host,
            "port": cfg.server.port,
        },
    }


def _dict_to_config(d: dict) -> AmberConfig:
    """Build an AmberConfig from a parsed TOML dict, falling back to defaults."""
    storage_d = d.get("storage", {})
    transcription_d = d.get("transcription", {})
    recording_d = d.get("recording", {})
    server_d = d.get("server", {})

    return AmberConfig(
        storage=StorageConfig(**{
            k: v for k, v in storage_d.items()
            if k in StorageConfig.__dataclass_fields__
        }),
        transcription=TranscriptionConfig(**{
            k: v for k, v in transcription_d.items()
            if k in TranscriptionConfig.__dataclass_fields__
        }),
        recording=RecordingConfig(**{
            k: v for k, v in recording_d.items()
            if k in RecordingConfig.__dataclass_fields__
        }),
        server=ServerConfig(**{
            k: v for k, v in server_d.items()
            if k in ServerConfig.__dataclass_fields__
        }),
    )


def load_config(config_path: Path | None = None) -> AmberConfig:
    """Load config from a TOML file.

    If no path is given, looks for data/config.toml relative to the project
    root. If the file doesn't exist, creates it with sensible defaults.
    """
    if config_path is None:
        config_path = PROJECT_ROOT / "data" / "config.toml"

    if config_path.exists():
        raw = config_path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
        return _dict_to_config(data)

    # First run: create default config
    cfg = AmberConfig()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_bytes(tomli_w.dumps(_config_to_dict(cfg)).encode("utf-8"))
    return cfg
