"""Engagement gate — turns raw detections into a smoothed boolean signal.

A face counts as *engaged* this frame if it is both close enough (bbox height
ratio) and facing the screen (|yaw| under threshold, or yaw unavailable). A
rolling majority window removes flicker, and a monotonic clock tracks how long
engagement has been continuously held so the state machine can debounce ARMING
without any blocking sleeps.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from controller.config import EngagementConfig, PrewarmConfig
from controller.detector.base import PresenceResult


@dataclass
class EngagementSignal:
    engaged: bool          # smoothed: close + facing
    approaching: bool      # smoothed: looser distance, for optional pre-warm
    engaged_for_s: float   # continuous seconds `engaged` has been True (0 if False)
    raw_engaged: bool      # this frame only, pre-smoothing (for debug overlay)
    bbox_height_ratio: float  # of the largest face this frame (0 if none)
    yaw: float | None      # of the largest face this frame


class EngagementGate:
    def __init__(
        self,
        cfg: EngagementConfig,
        prewarm: PrewarmConfig,
        *,
        clock=time.monotonic,
    ) -> None:
        self.cfg = cfg
        self.prewarm = prewarm
        self._clock = clock
        window = max(1, cfg.smoothing_window)
        self._engaged_window: deque[bool] = deque(maxlen=window)
        self._approach_window: deque[bool] = deque(maxlen=window)
        self._engaged_since: float | None = None
        self._smoothed_engaged = False

    def _majority(self, window: deque[bool]) -> bool:
        if not window:
            return False
        return sum(window) * 2 > len(window)

    def update(self, result: PresenceResult) -> EngagementSignal:
        face = result.largest_face()
        frame_h = result.frame_height or 1

        ratio = 0.0
        yaw = None
        raw_engaged = False
        raw_approaching = False

        if face is not None:
            ratio = face.height / frame_h
            yaw = face.yaw_degrees
            close_enough = ratio >= self.cfg.min_bbox_height_ratio
            facing = yaw is None or abs(yaw) <= self.cfg.max_yaw_degrees
            raw_engaged = close_enough and facing
            raw_approaching = ratio >= self.prewarm.approach_bbox_height_ratio

        self._engaged_window.append(raw_engaged)
        self._approach_window.append(raw_approaching)

        smoothed = self._majority(self._engaged_window)
        approaching = self._majority(self._approach_window)

        now = self._clock()
        if smoothed and not self._smoothed_engaged:
            self._engaged_since = now
        elif not smoothed:
            self._engaged_since = None
        self._smoothed_engaged = smoothed

        engaged_for = (now - self._engaged_since) if self._engaged_since is not None else 0.0

        return EngagementSignal(
            engaged=smoothed,
            approaching=approaching,
            engaged_for_s=engaged_for,
            raw_engaged=raw_engaged,
            bbox_height_ratio=ratio,
            yaw=yaw,
        )
