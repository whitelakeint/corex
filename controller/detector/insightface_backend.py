"""InsightFace backend — highest-quality face + head pose.

Returns accurate bounding boxes and a real yaw/pitch/roll estimate, giving the
best engagement gate quality. This is the upgrade path from the mediapipe
default. Requires ``insightface`` + ``onnxruntime`` (use ``onnxruntime-gpu`` and
set ``detector.insightface_ctx_id`` >= 0 for GPU inference).
"""

from __future__ import annotations

from controller.config import DetectorConfig
from controller.detector.base import Face, PresenceResult


class InsightFaceDetector:
    def __init__(self, cfg: DetectorConfig) -> None:
        from insightface.app import FaceAnalysis

        self.cfg = cfg
        self._app = FaceAnalysis(name=cfg.insightface_model)
        self._app.prepare(
            ctx_id=cfg.insightface_ctx_id,
            det_size=(640, 640),
        )

    def detect(self, frame) -> PresenceResult:
        h = frame.shape[0]
        detections = self._app.get(frame)

        faces: list[Face] = []
        for det in detections:
            score = float(getattr(det, "det_score", 0.0))
            if score < self.cfg.min_confidence:
                continue
            x1, y1, x2, y2 = (float(v) for v in det.bbox)
            fw = x2 - x1
            fh = y2 - y1

            yaw = None
            pose = getattr(det, "pose", None)
            if pose is not None and len(pose) >= 1:
                # insightface pose = [yaw, pitch, roll]
                yaw = abs(float(pose[0]))

            faces.append(
                Face(
                    bbox=(int(x1), int(y1), int(fw), int(fh)),
                    confidence=score,
                    yaw_degrees=yaw,
                )
            )

        return PresenceResult(faces=faces, frame_height=h)

    def close(self) -> None:
        self._app = None
