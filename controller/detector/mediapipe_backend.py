"""MediaPipe Face Detection backend (the spec default).

CPU-only, cross-platform, light — good for mini-PC kiosks. MediaPipe returns 6
keypoints (both eyes, nose tip, mouth, both ear tragions). We estimate a rough
yaw from the horizontal asymmetry of the eyes about the nose: when the head
turns, one eye moves closer to the nose in image space than the other.
"""

from __future__ import annotations

import mediapipe as mp

from controller.config import DetectorConfig
from controller.detector.base import Face, PresenceResult

# Keypoint indices per MediaPipe Face Detection spec.
_RIGHT_EYE = 0
_LEFT_EYE = 1
_NOSE = 2


class MediaPipeDetector:
    def __init__(self, cfg: DetectorConfig) -> None:
        self.cfg = cfg
        self._fd = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # 1 = full-range, better for people a bit further off
            min_detection_confidence=cfg.min_confidence,
        )

    def _estimate_yaw(self, kp, frame_w: int) -> float | None:
        """Coarse yaw from eye-vs-nose horizontal asymmetry, in degrees."""
        try:
            rx = kp[_RIGHT_EYE].x
            lx = kp[_LEFT_EYE].x
            nx = kp[_NOSE].x
        except (IndexError, AttributeError):
            return None

        eye_span = abs(lx - rx)
        if eye_span < 1e-4:
            return None
        # nose offset from the eye midpoint, normalised by eye span; 0 = centred.
        midpoint = (lx + rx) / 2.0
        ratio = (nx - midpoint) / eye_span
        # Map the ratio onto a plausible +/-60 degree range and clamp.
        yaw = max(-60.0, min(60.0, ratio * 90.0))
        return abs(yaw)  # sign is irrelevant to the |yaw| gate

    def detect(self, frame) -> PresenceResult:
        import cv2  # local import keeps base deps minimal for other backends

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._fd.process(rgb)

        faces: list[Face] = []
        if result.detections:
            for det in result.detections:
                score = det.score[0] if det.score else 0.0
                box = det.location_data.relative_bounding_box
                x = int(box.xmin * w)
                y = int(box.ymin * h)
                fw = int(box.width * w)
                fh = int(box.height * h)
                kp = det.location_data.relative_keypoints
                yaw = self._estimate_yaw(kp, w)
                faces.append(
                    Face(bbox=(x, y, fw, fh), confidence=float(score), yaw_degrees=yaw)
                )

        return PresenceResult(faces=faces, frame_height=h)

    def close(self) -> None:
        self._fd.close()
