"""FSM transition tests. No camera, no network — pure logic with a fake clock."""

from __future__ import annotations

from unittest.mock import MagicMock

from controller.config import EngagementConfig
from controller.engagement import EngagementSignal
from controller.state_machine import Callbacks, State, StateMachine


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _signal(engaged: bool, held: float = 0.0) -> EngagementSignal:
    return EngagementSignal(
        engaged=engaged,
        approaching=engaged,
        engaged_for_s=held,
        raw_engaged=engaged,
        bbox_height_ratio=0.25 if engaged else 0.0,
        yaw=0.0,
    )


def _make(clock: FakeClock):
    cb = Callbacks(
        start_conversation=MagicMock(),
        end_conversation=MagicMock(),
        show_attract=MagicMock(),
        show_greeting=MagicMock(),
        show_conversation=MagicMock(),
        on_transition=MagicMock(),
    )
    cfg = EngagementConfig(arm_debounce_s=1.5, grace_s=12.0)
    fsm = StateMachine(cfg, cb, use_greeting_bridge=True, clock=clock)
    return fsm, cb


def test_starts_idle_and_shows_attract():
    fsm, cb = _make(FakeClock())
    assert fsm.state is State.IDLE
    cb.show_attract.assert_called_once()


def test_idle_to_arming_requires_debounce():
    clock = FakeClock()
    fsm, cb = _make(clock)

    # Engaged but not long enough — stays IDLE.
    fsm.on_tick(_signal(True, held=1.0))
    assert fsm.state is State.IDLE
    cb.start_conversation.assert_not_called()

    # Held past debounce — arms and kicks off create + greeting bridge.
    fsm.on_tick(_signal(True, held=1.6))
    assert fsm.state is State.ARMING
    cb.show_greeting.assert_called_once()
    cb.start_conversation.assert_called_once()


def test_arming_to_active_on_created():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.notify_conversation_started("https://room")
    assert fsm.state is State.ACTIVE
    cb.show_conversation.assert_called_once_with("https://room")


def test_arming_aborts_if_engagement_lost():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.on_tick(_signal(False))
    assert fsm.state is State.IDLE


def test_active_to_grace_to_idle_ends_room():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.notify_conversation_started("https://room")

    # Engagement lost -> GRACE, room still open.
    fsm.on_tick(_signal(False))
    assert fsm.state is State.GRACE
    cb.end_conversation.assert_not_called()

    # Within grace, nothing happens.
    clock.advance(5.0)
    fsm.on_tick(_signal(False))
    assert fsm.state is State.GRACE

    # Grace expires -> end room + IDLE.
    clock.advance(8.0)
    fsm.on_tick(_signal(False))
    assert fsm.state is State.IDLE
    cb.end_conversation.assert_called_once()


def test_grace_cancelled_when_face_returns():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.notify_conversation_started("https://room")
    fsm.on_tick(_signal(False))
    assert fsm.state is State.GRACE

    clock.advance(3.0)
    fsm.on_tick(_signal(True, held=0.1))
    assert fsm.state is State.ACTIVE
    cb.end_conversation.assert_not_called()


def test_create_failure_backs_off_before_rearm():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    assert fsm.state is State.ARMING

    fsm.notify_conversation_failed("boom")
    assert fsm.state is State.IDLE

    # Immediately engaged again, but backoff blocks re-arming.
    fsm.on_tick(_signal(True, held=2.0))
    assert fsm.state is State.IDLE

    # After backoff window, arming is allowed again.
    clock.advance(5.0)
    fsm.on_tick(_signal(True, held=2.0))
    assert fsm.state is State.ARMING


def test_room_ended_externally_returns_to_idle():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.notify_conversation_started("https://room")
    fsm.notify_room_ended("poll:ended")
    assert fsm.state is State.IDLE


def test_force_idle_ends_open_room():
    clock = FakeClock()
    fsm, cb = _make(clock)
    fsm.on_tick(_signal(True, held=2.0))
    fsm.notify_conversation_started("https://room")
    fsm.force_idle("shutdown")
    assert fsm.state is State.IDLE
    cb.end_conversation.assert_called_once()
