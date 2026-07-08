"""Engagement gate tests — distance proxy, yaw gate, smoothing, dwell timer."""

from __future__ import annotations

from controller.config import EngagementConfig, PrewarmConfig
from controller.detector.base import Face, PresenceResult
from controller.engagement import EngagementGate


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


FRAME_H = 480


def _result(ratio: float | None, yaw: float | None = 0.0) -> PresenceResult:
    if ratio is None:
        return PresenceResult(faces=[], frame_height=FRAME_H)
    h = int(ratio * FRAME_H)
    face = Face(bbox=(100, 100, h, h), confidence=0.9, yaw_degrees=yaw)
    return PresenceResult(faces=[face], frame_height=FRAME_H)


def _gate(clock=None, window=5):
    cfg = EngagementConfig(
        min_bbox_height_ratio=0.18,
        max_yaw_degrees=25.0,
        smoothing_window=window,
    )
    prewarm = PrewarmConfig(approach_bbox_height_ratio=0.10)
    return EngagementGate(cfg, prewarm, clock=clock or FakeClock())


def _drive(gate, result, n):
    sig = None
    for _ in range(n):
        sig = gate.update(result)
    return sig


def test_close_and_facing_becomes_engaged():
    gate = _gate(window=5)
    sig = _drive(gate, _result(0.25, yaw=5.0), 5)
    assert sig.engaged is True


def test_far_is_not_engaged():
    gate = _gate(window=5)
    sig = _drive(gate, _result(0.10, yaw=0.0), 5)
    assert sig.engaged is False


def test_looking_away_is_not_engaged():
    gate = _gate(window=5)
    sig = _drive(gate, _result(0.30, yaw=45.0), 5)
    assert sig.engaged is False


def test_yaw_none_falls_back_to_distance_only():
    # YOLO-style detection: no pose. Close enough should still engage.
    gate = _gate(window=5)
    sig = _drive(gate, _result(0.30, yaw=None), 5)
    assert sig.engaged is True


def test_no_face_is_not_engaged():
    gate = _gate(window=5)
    sig = _drive(gate, _result(None), 5)
    assert sig.engaged is False
    assert sig.bbox_height_ratio == 0.0


def test_smoothing_ignores_single_frame_flicker():
    gate = _gate(window=5)
    # Fill window with "not engaged".
    _drive(gate, _result(0.05), 5)
    # One engaged frame shouldn't flip the majority.
    sig = gate.update(_result(0.30))
    assert sig.engaged is False


def test_dwell_timer_accumulates():
    clock = FakeClock()
    gate = _gate(clock=clock, window=1)  # window=1 => instant majority
    gate.update(_result(0.30))           # engaged at t=0
    clock.advance(2.0)
    sig = gate.update(_result(0.30))
    assert sig.engaged is True
    assert sig.engaged_for_s >= 2.0


def test_dwell_resets_on_disengage():
    clock = FakeClock()
    gate = _gate(clock=clock, window=1)
    gate.update(_result(0.30))
    clock.advance(2.0)
    gate.update(_result(0.05))           # disengage
    clock.advance(1.0)
    sig = gate.update(_result(0.30))     # re-engage; timer restarts
    assert sig.engaged_for_s < 0.5


def test_approaching_uses_looser_threshold():
    gate = _gate(window=1)
    # ratio between approach (0.10) and engage (0.18): approaching but not engaged.
    sig = gate.update(_result(0.14, yaw=0.0))
    assert sig.approaching is True
    assert sig.engaged is False
