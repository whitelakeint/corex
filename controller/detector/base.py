"""Detector interface + shared value types.

A backend turns one camera frame into a list of :class:`Face` detections. The
engagement gate (not the backend) decides whether any face is *engaged*; the
backend's only job is to report faces, bounding boxes, confidence, and — where
it can — an approximate head yaw so "facing the screen" can be judged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Face:
    bbox: tuple[int, int, int, int]      # x, y, w, h in pixels
    confidence: float
    yaw_degrees: float | None = None     # +/- from frontal; None if unavailable
    keypoints: dict | None = None        # eyes/nose/mouth if available

    @property
    def height(self) -> int:
        return self.bbox[3]

    @property
    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]


@dataclass
class PresenceResult:
    faces: list[Face]
    frame_height: int

    def largest_face(self) -> Face | None:
        """The closest (largest-area) face, or None if the frame is empty."""
        if not self.faces:
            return None
        return max(self.faces, key=lambda f: f.area)


@runtime_checkable
class PresenceDetector(Protocol):
    def detect(self, frame) -> PresenceResult:
        """Run detection on a single BGR frame (numpy array)."""
        ...

    def close(self) -> None:
        """Release camera/model resources."""
        ...
