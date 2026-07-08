"""Presence controller entrypoint.

Wires the camera, detector, engagement gate, FSM, Tavus client and frontend
WebSocket into one asyncio application. The FSM stays pure/synchronous; its
side-effect callbacks schedule async work here (Tavus create/end, WS sends) so
nothing ever blocks the tick loop.

Run:
    python -m controller.main                 # normal
    python -m controller.main --debug-overlay # tuning window with bbox/yaw/state
    python -m controller.main --config path/to/config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timezone

import cv2

from controller.config import Config, load_config
from controller.detector import create_detector
from controller.detector.base import PresenceResult
from controller.engagement import EngagementGate, EngagementSignal
from controller.frontend_link import FrontendLink
from controller.state_machine import Callbacks, State, StateMachine
from controller.tavus_client import TavusClient

logger = logging.getLogger("kiosk.main")


class KioskController:
    def __init__(self, cfg: Config, *, debug_overlay: bool = False) -> None:
        self.cfg = cfg
        self.debug_overlay = debug_overlay

        self.detector = create_detector(cfg.detector)
        self.gate = EngagementGate(cfg.engagement, cfg.prewarm)
        self.tavus = TavusClient(cfg)
        self.link = FrontendLink(
            cfg.frontend.ws_host, cfg.frontend.ws_port, on_event=self._on_frontend_event
        )

        self._loop = asyncio.get_event_loop()
        self._tasks: set[asyncio.Task] = set()
        self._stopping = asyncio.Event()

        # Session bookkeeping.
        self.conversation_id: str | None = None
        self.conversation_url: str | None = None
        self._session_start_wall: str | None = None
        self._session_start_mono: float | None = None
        self._creating = False
        self._sessions = 0
        self._false_arms = 0

        callbacks = Callbacks(
            start_conversation=lambda: self._spawn(self._create_conversation()),
            end_conversation=lambda: self._spawn(self._end_conversation("grace_expired")),
            show_attract=lambda: self._spawn(self.link.show_attract()),
            show_greeting=lambda: self._spawn(self.link.show_greeting()),
            show_conversation=lambda url: self._spawn(self.link.show_conversation(url)),
            on_transition=self._on_transition,
        )
        self.fsm = StateMachine(
            cfg.engagement,
            callbacks,
            use_greeting_bridge=cfg.frontend.use_greeting_bridge,
        )

        self._last_result: PresenceResult | None = None
        self._last_signal: EngagementSignal | None = None

    # -- task plumbing -------------------------------------------------------
    def _spawn(self, coro) -> None:
        task = self._loop.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # -- FSM transition side channel (metrics) -------------------------------
    def _on_transition(self, frm: State, to: State, reason: str) -> None:
        if frm is State.ARMING and to is State.IDLE:
            self._false_arms += 1
            logger.info("False arm (#%d): %s", self._false_arms, reason)
        if to is State.ACTIVE and frm is State.ARMING:
            self._sessions += 1

    # -- Tavus lifecycle -----------------------------------------------------
    async def _create_conversation(self) -> None:
        if self._creating or self.conversation_id is not None:
            return
        self._creating = True
        name = "kiosk-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            data = await self.tavus.create(name)
            cid = data.get("conversation_id")
            url = data.get("conversation_url")
            if not url or not cid:
                raise RuntimeError(f"Tavus returned no room: {data}")

            if self.fsm.state is State.ARMING:
                self.conversation_id = cid
                self.conversation_url = url
                self._session_start_wall = datetime.now(timezone.utc).isoformat()
                self._session_start_mono = time.monotonic()
                logger.info("Conversation created: %s", cid)
                self.fsm.notify_conversation_started(url)
            else:
                # Visitor left while we were spinning up — reap the orphan room.
                logger.info("Left during ARMING; ending orphan room %s", cid)
                await self.tavus.end(cid)
        except Exception as exc:  # noqa: BLE001
            logger.error("Create failed: %s", exc)
            self.fsm.notify_conversation_failed(str(exc))
        finally:
            self._creating = False

    async def _end_conversation(self, reason: str) -> None:
        cid = self.conversation_id
        self.conversation_id = None
        self.conversation_url = None
        if not cid:
            return
        if self.cfg.logging.session_metrics and self._session_start_mono is not None:
            billed = time.monotonic() - self._session_start_mono
            logger.info(
                "SESSION_END conversation_id=%s start=%s billed_seconds=%.1f reason=%s "
                "sessions=%d false_arms=%d",
                cid, self._session_start_wall, billed, reason, self._sessions, self._false_arms,
            )
        self._session_start_mono = None
        self._session_start_wall = None
        await self.tavus.end(cid)

    async def _on_frontend_event(self, event: str, msg: dict) -> None:
        logger.info("Frontend event: %s", event)
        if event == "room_ended":
            await self._end_conversation("frontend_room_ended")
            self.fsm.notify_room_ended("frontend room_ended")
        # room_joined needs no action — the room layer is already shown.

    # -- background poll (server-side shutdown detection) --------------------
    async def _poll_loop(self) -> None:
        interval = max(5, self.cfg.tavus_poll.interval_s)
        while not self._stopping.is_set():
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            if self.fsm.state not in (State.ACTIVE, State.GRACE):
                continue
            cid = self.conversation_id
            if not cid:
                continue
            try:
                data = await self.tavus.get(cid)
                status = (data.get("status") or "").lower()
                if status in ("ended", "completed", "expired", "error"):
                    logger.info("Poll: room %s ended server-side (%s)", cid, status)
                    self.conversation_id = None
                    self.conversation_url = None
                    self._session_start_mono = None
                    self.fsm.notify_room_ended(f"poll:{status}")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Poll error for %s: %s", cid, exc)

    # -- camera loop ---------------------------------------------------------
    def _open_camera(self):
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.cfg.camera.device_index, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.camera.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.camera.frame_height)
        return cap

    async def _camera_loop(self) -> None:
        frame_interval = 1.0 / max(1, self.cfg.camera.target_fps)
        cap = None
        try:
            while not self._stopping.is_set():
                if cap is None or not cap.isOpened():
                    cap = await self._loop.run_in_executor(None, self._open_camera)
                    if not cap.isOpened():
                        logger.error("Camera %d unavailable; retrying in 3s", self.cfg.camera.device_index)
                        self.fsm.force_idle("camera unavailable")
                        await asyncio.sleep(3.0)
                        continue
                    logger.info("Camera %d opened", self.cfg.camera.device_index)

                tick_start = time.monotonic()
                ret, frame = await self._loop.run_in_executor(None, cap.read)
                if not ret or frame is None:
                    logger.warning("Camera read failed; reopening")
                    self.fsm.force_idle("camera read failure")
                    cap.release()
                    cap = None
                    await asyncio.sleep(1.0)
                    continue

                result = await self._loop.run_in_executor(None, self.detector.detect, frame)
                signal = self.gate.update(result)
                self._last_result = result
                self._last_signal = signal
                self.fsm.on_tick(signal)

                if self.debug_overlay:
                    if not self._render_overlay(frame, result, signal):
                        self._stopping.set()
                        break

                elapsed = time.monotonic() - tick_start
                await asyncio.sleep(max(0.0, frame_interval - elapsed))
        finally:
            if cap is not None:
                cap.release()
            if self.debug_overlay:
                cv2.destroyAllWindows()

    def _render_overlay(self, frame, result: PresenceResult, signal: EngagementSignal) -> bool:
        """Draw the tuning HUD. Returns False if the user pressed q/ESC."""
        largest = result.largest_face()
        for face in result.faces:
            x, y, w, h = face.bbox
            colour = (0, 200, 0) if face is largest else (120, 120, 120)
            cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 2)

        lines = [
            f"state={self.fsm.state.value}",
            f"engaged={signal.engaged} approaching={signal.approaching}",
            f"raw={signal.raw_engaged} held={signal.engaged_for_s:.1f}s",
            f"bbox_ratio={signal.bbox_height_ratio:.3f} yaw={signal.yaw}",
        ]
        grace = self.fsm.grace_remaining
        if grace is not None:
            lines.append(f"grace_remaining={grace:.1f}s")
        for i, text in enumerate(lines):
            cv2.putText(frame, text, (10, 24 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, text, (10, 24 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow("kiosk presence (q to quit)", frame)
        key = cv2.waitKey(1) & 0xFF
        return key not in (ord("q"), 27)

    # -- lifecycle -----------------------------------------------------------
    async def run(self) -> None:
        await self.link.start()
        poll_task = self._loop.create_task(self._poll_loop())
        try:
            await self._camera_loop()
        finally:
            self._stopping.set()
            poll_task.cancel()
            await self.shutdown()

    async def shutdown(self) -> None:
        logger.info("Shutting down; ending any open room")
        # Ensure billing stops even on crash/exit.
        self.fsm.force_idle("controller shutdown")
        if self.conversation_id:
            await self._end_conversation("shutdown")
        try:
            self.detector.close()
        except Exception:  # noqa: BLE001
            pass
        await self.link.stop()


async def _amain(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper(), logging.INFO),
        format="%(asctime)s  %(name)-16s  %(levelname)-5s  %(message)s",
    )

    if not cfg.api_key:
        logger.error("TAVUS_API_KEY not set (put it in .env). Aborting.")
        return
    if not cfg.tavus.persona_id:
        logger.error("persona_id not set (config.yaml or TAVUS_PERSONA_ID). Aborting.")
        return

    logger.info(
        "Kiosk controller: property=%r backend=%s ws=%s",
        cfg.property.name, cfg.detector.backend, cfg.ws_url(),
    )
    controller = KioskController(cfg, debug_overlay=args.debug_overlay)

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, controller._stopping.set)

    await controller.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Presence-gated Tavus kiosk controller")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--debug-overlay", action="store_true",
                        help="Show a preview window with bbox/yaw/state for tuning")
    args = parser.parse_args()
    try:
        asyncio.run(_amain(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
