"""Pluggable presence-detector backends.

All backends implement the :class:`~controller.detector.base.PresenceDetector`
interface and are selected by name from config (``detector.backend``).
"""

from __future__ import annotations

from controller.config import DetectorConfig
from controller.detector.base import Face, PresenceDetector, PresenceResult

__all__ = ["Face", "PresenceResult", "PresenceDetector", "create_detector"]


def create_detector(cfg: DetectorConfig) -> PresenceDetector:
    """Factory: instantiate the configured detector backend.

    Imports are lazy so a box only needs the deps for the backend it runs.
    """
    backend = cfg.backend.lower()

    if backend == "opencv":
        from controller.detector.opencv_backend import OpenCVDetector

        return OpenCVDetector(cfg)
    if backend == "mediapipe":
        from controller.detector.mediapipe_backend import MediaPipeDetector

        return MediaPipeDetector(cfg)
    if backend == "yolo":
        from controller.detector.yolo_backend import YoloDetector

        return YoloDetector(cfg)
    if backend == "insightface":
        from controller.detector.insightface_backend import InsightFaceDetector

        return InsightFaceDetector(cfg)

    raise ValueError(
        f"Unknown detector backend '{cfg.backend}'. "
        "Expected one of: opencv, mediapipe, yolo, insightface."
    )
