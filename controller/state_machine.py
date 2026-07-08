"""The 4-state presence lifecycle FSM.

    IDLE  --engaged for arm_debounce_s-->  ARMING
    ARMING --create OK-->  ACTIVE          ARMING --lost/create-fail--> IDLE
    ACTIVE --engagement lost-->  GRACE     ACTIVE --room ended--> IDLE
    GRACE --face returns-->  ACTIVE        GRACE --grace_s elapsed--> end + IDLE

Hysteresis is deliberate: **fast to arm, slow to release**. The FSM is pure and
synchronous — it never awaits. Async work (Tavus create/end, WebSocket sends)
lives in injected callbacks; because create is asynchronous, ARMING->ACTIVE is
driven by :meth:`notify_conversation_started`, not from inside ``on_tick``.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass
from typing import Callable

from controller.config import EngagementConfig
from controller.engagement import EngagementSignal

logger = logging.getLogger("kiosk.fsm")


class State(enum.Enum):
    IDLE = "IDLE"
    ARMING = "ARMING"
    ACTIVE = "ACTIVE"
    GRACE = "GRACE"


@dataclass
class Callbacks:
    """Injected side effects. In production these schedule async work; in tests
    they are plain mocks. All are optional no-ops by default."""

    start_conversation: Callable[[], None] = lambda: None
    end_conversation: Callable[[], None] = lambda: None
    show_attract: Callable[[], None] = lambda: None
    show_greeting: Callable[[], None] = lambda: None
    show_conversation: Callable[[str], None] = lambda url: None
    on_transition: Callable[[State, State, str], None] = lambda a, b, r: None


class StateMachine:
    def __init__(
        self,
        cfg: EngagementConfig,
        callbacks: Callbacks,
        *,
        use_greeting_bridge: bool = True,
        clock: Callable[[], float] = time.monotonic,
        backoff_base_s: float = 2.0,
        backoff_max_s: float = 30.0,
    ) -> None:
        self.cfg = cfg
        self.cb = callbacks
        self.use_greeting_bridge = use_greeting_bridge
        self._clock = clock
        self._backoff_base = backoff_base_s
        self._backoff_max = backoff_max_s

        self.state = State.IDLE
        self._grace_deadline: float | None = None
        self._next_arm_allowed: float = 0.0
        self._backoff_s: float = backoff_base_s

        # Enter IDLE cleanly (show the attract loop from the start).
        self.cb.show_attract()

    # -- transition helper ---------------------------------------------------
    def _transition(self, to: State, reason: str) -> None:
        frm = self.state
        if frm is to:
            return
        self.state = to
        logger.info("FSM %s -> %s (%s)", frm.value, to.value, reason)
        self.cb.on_transition(frm, to, reason)

    # -- main driver ---------------------------------------------------------
    def on_tick(self, signal: EngagementSignal) -> None:
        now = self._clock()

        if self.state is State.IDLE:
            if (
                signal.engaged
                and signal.engaged_for_s >= self.cfg.arm_debounce_s
                and now >= self._next_arm_allowed
            ):
                self._transition(State.ARMING, "engaged past debounce")
                # Show the greeting bridge immediately to mask cold-start latency.
                if self.use_greeting_bridge:
                    self.cb.show_greeting()
                self.cb.start_conversation()

        elif self.state is State.ARMING:
            # Wait for notify_conversation_started / _failed. Bail if they leave.
            if not signal.engaged:
                self._transition(State.IDLE, "engagement lost during ARMING")
                self.cb.show_attract()

        elif self.state is State.ACTIVE:
            if not signal.engaged:
                self._grace_deadline = now + self.cfg.grace_s
                self._transition(State.GRACE, "engagement lost")

        elif self.state is State.GRACE:
            if signal.engaged:
                self._grace_deadline = None
                self._transition(State.ACTIVE, "face returned within grace")
            elif self._grace_deadline is not None and now >= self._grace_deadline:
                self._grace_deadline = None
                self._transition(State.IDLE, "grace expired")
                self.cb.end_conversation()
                self.cb.show_attract()

    # -- async completions / external events ---------------------------------
    def notify_conversation_started(self, url: str) -> None:
        """Tavus create succeeded and returned a room URL."""
        if self.state is not State.ARMING:
            # Person left before the room was ready — caller should end the room.
            logger.warning("Room ready but state=%s; not activating", self.state.value)
            return
        self._backoff_s = self._backoff_base  # success resets backoff
        self._transition(State.ACTIVE, "conversation created")
        self.cb.show_conversation(url)

    def notify_conversation_failed(self, reason: str = "create failed") -> None:
        """Tavus create failed — back off before we try to arm again."""
        now = self._clock()
        self._next_arm_allowed = now + self._backoff_s
        self._backoff_s = min(self._backoff_max, self._backoff_s * 2)
        if self.state is State.ARMING:
            self._transition(State.IDLE, reason)
            self.cb.show_attract()

    def notify_room_ended(self, reason: str = "room ended") -> None:
        """Room was shut down externally (Tavus timeout, max duration, frontend
        leave). Sync the FSM back to IDLE."""
        if self.state in (State.ACTIVE, State.GRACE):
            self._grace_deadline = None
            self._transition(State.IDLE, reason)
            self.cb.show_attract()

    def force_idle(self, reason: str) -> None:
        """Hard reset (camera failure, shutdown). Ends any open room."""
        if self.state in (State.ACTIVE, State.GRACE):
            self.cb.end_conversation()
        if self.state is not State.IDLE:
            self._grace_deadline = None
            self._transition(State.IDLE, reason)
            self.cb.show_attract()

    # -- introspection (debug overlay / metrics) -----------------------------
    @property
    def grace_remaining(self) -> float | None:
        if self._grace_deadline is None:
            return None
        return max(0.0, self._grace_deadline - self._clock())
