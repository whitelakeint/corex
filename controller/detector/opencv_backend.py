"""OpenCV Haar-cascade backend.

Zero extra dependencies beyond ``opencv-python`` — the fastest way to get the
kiosk detecting faces on any box, including a plain Windows dev machine. Yaw is
estimated coarsely from the horizontal offset of a detected profile face, so the
engagement gate still gets a "facing the screen" signal (approximate).
"""

from __future__ import annotations

import cv2

from controller.config import DetectorConfig
from controller.detector.base import Face, PresenceResult


class OpenCVDetector:
    def __init__(self, cfg: DetectorConfig) -> None:
        self.cfg = cfg
        base = cv2.data.haarcascades
        self._frontal = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
        self._profile = cv2.CascadeClassifier(base + "haarcascade_profileface.xml")
        if self._frontal.empty():
            raise RuntimeError("Failed to load OpenCV frontal-face Haar cascade")

    def detect(self, frame) -> PresenceResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        h = frame.shape[0]

        frontal = self._frontal.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60)
        )
        faces: list[Face] = []
        for (x, y, fw, fh) in frontal:
            # A confidently detected frontal face => yaw ~ 0 (facing us).
            faces.append(Face(bbox=(int(x), int(y), int(fw), int(fh)),
                              confidence=0.8, yaw_degrees=0.0))

        # If no frontal face, a profile detection means the head is turned.
        if not faces and not self._profile.empty():
            profile = self._profile.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=6, minSize=(60, 60)
            )
            for (x, y, fw, fh) in profile:
                faces.append(Face(bbox=(int(x), int(y), int(fw), int(fh)),
                                  confidence=0.6, yaw_degrees=45.0))

        return PresenceResult(faces=faces, frame_height=h)

    def close(self) -> None:  # cascades hold no resources needing release
        pass
