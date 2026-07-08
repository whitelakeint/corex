"""Ultralytics YOLO backend (for a box with a GPU).

Runs a nano model and treats detected *persons* as presence. YOLO person boxes
don't give head pose, so ``yaw_degrees`` is ``None`` — the engagement gate then
falls back to bbox-size + presence only (see engagement.py). We approximate a
"face height" from the top portion of the person box so the same
``min_bbox_height_ratio`` distance proxy keeps working.
"""

from __future__ import annotations

from controller.config import DetectorConfig
from controller.detector.base import Face, PresenceResult

# COCO class id 0 == "person".
_PERSON_CLASS = 0
# Fraction of a standing-person box that is roughly head height.
_HEAD_FRACTION = 0.22


class YoloDetector:
    def __init__(self, cfg: DetectorConfig) -> None:
        from ultralytics import YOLO

        self.cfg = cfg
        self._model = YOLO(cfg.yolo_model)

    def detect(self, frame) -> PresenceResult:
        h = frame.shape[0]
        results = self._model.predict(
            frame, classes=[_PERSON_CLASS], conf=self.cfg.min_confidence, verbose=False
        )

        faces: list[Face] = []
        for res in results:
            boxes = getattr(res, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                conf = float(box.conf[0]) if box.conf is not None else 0.0
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                pw = x2 - x1
                ph = y2 - y1
                # Approximate the head region (top of the person box).
                head_h = ph * _HEAD_FRACTION
                faces.append(
                    Face(
                        bbox=(int(x1), int(y1), int(pw), int(head_h)),
                        confidence=conf,
                        yaw_degrees=None,  # no pose from a person box
                    )
                )

        return PresenceResult(faces=faces, frame_height=h)

    def close(self) -> None:
        self._model = None
