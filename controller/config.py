"""Typed configuration for the presence controller.

Loaded from a YAML file (default: ``config.yaml`` at the repo root) with a small
number of environment overrides so secrets and per-site values never need to be
committed. The one required secret, ``TAVUS_API_KEY``, is read from the
environment / project ``.env`` (reusing :mod:`backend.config`'s dotenv load).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# Reuse the backend's .env loading + Tavus credentials so both processes agree.
from backend.config import (
    TAVUS_API_KEY,
    TAVUS_PERSONA_ID,
    TAVUS_REPLICA_ID,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class PropertyConfig(BaseModel):
    name: str = "The Meridian"
    conversational_context: str | None = None

    def context(self) -> str:
        """Return the conversational context, auto-building one if unset."""
        if self.conversational_context:
            return self.conversational_context.replace("{property_name}", self.name)
        return (
            f"You are a friendly, professional AI concierge at {self.name}. "
            "Greet the visitor warmly, help with visitor check-in, directions, "
            "leasing enquiries, deliveries and amenities, and escalate to a human "
            "team member when asked or when you cannot help."
        )


class TavusConfig(BaseModel):
    replica_id: str = ""
    persona_id: str = ""
    max_call_duration: int = 600
    participant_left_timeout: int = 20
    participant_absent_timeout: int = 60
    enable_recording: bool = False
    callback_url: str | None = None


class CameraConfig(BaseModel):
    device_index: int = 0
    target_fps: int = 10
    frame_width: int = 640
    frame_height: int = 480


class DetectorConfig(BaseModel):
    backend: str = "opencv"
    min_confidence: float = 0.6
    yolo_model: str = "yolov8n.pt"
    insightface_model: str = "buffalo_l"
    insightface_ctx_id: int = -1


class EngagementConfig(BaseModel):
    min_bbox_height_ratio: float = 0.18
    max_yaw_degrees: float = 25.0
    arm_debounce_s: float = 1.5
    grace_s: float = 12.0
    smoothing_window: int = 5


class PrewarmConfig(BaseModel):
    enabled: bool = False
    approach_bbox_height_ratio: float = 0.10


class FrontendConfig(BaseModel):
    ws_host: str = "127.0.0.1"
    ws_port: int = 8765
    attract_video: str = "media/attract.mp4"
    greeting_video: str = "media/greeting.mp4"
    use_greeting_bridge: bool = True
    greeting_bridge_ms: int = 3000


class TavusPollConfig(BaseModel):
    interval_s: int = 15


class LoggingConfig(BaseModel):
    level: str = "INFO"
    session_metrics: bool = True


class Config(BaseModel):
    property: PropertyConfig = Field(default_factory=PropertyConfig)
    tavus: TavusConfig = Field(default_factory=TavusConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    engagement: EngagementConfig = Field(default_factory=EngagementConfig)
    prewarm: PrewarmConfig = Field(default_factory=PrewarmConfig)
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)
    tavus_poll: TavusPollConfig = Field(default_factory=TavusPollConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Secret, never from YAML:
    api_key: str = ""

    # NOTE: a plain method, not a @property — the ``property`` field above
    # shadows the builtin ``property`` decorator inside this class body.
    def ws_url(self) -> str:
        return f"ws://{self.frontend.ws_host}:{self.frontend.ws_port}"


def _apply_env_overrides(cfg: Config) -> Config:
    """Environment beats YAML for secrets and per-machine values."""
    cfg.api_key = TAVUS_API_KEY

    # Credentials fall back to the backend env if the YAML left them blank.
    cfg.tavus.persona_id = cfg.tavus.persona_id or TAVUS_PERSONA_ID
    cfg.tavus.replica_id = cfg.tavus.replica_id or TAVUS_REPLICA_ID

    if os.getenv("PROPERTY_NAME"):
        cfg.property.name = os.environ["PROPERTY_NAME"]
    return cfg


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Load and validate controller config.

    Search order: explicit ``path`` -> ``$KIOSK_CONFIG`` -> ``config.yaml`` ->
    ``config.example.yaml`` (so a fresh checkout runs with sane defaults).
    """
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    if os.getenv("KIOSK_CONFIG"):
        candidates.append(Path(os.environ["KIOSK_CONFIG"]))
    candidates.append(REPO_ROOT / "config.yaml")
    candidates.append(REPO_ROOT / "config.example.yaml")

    raw: dict = {}
    for candidate in candidates:
        if candidate.is_file():
            with candidate.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            break

    cfg = Config.model_validate(raw)
    return _apply_env_overrides(cfg)
