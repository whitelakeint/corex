"""Local WebSocket bridge between the controller and the kiosk browser.

The controller pushes one of three commands — ``attract``, ``greeting``,
``conversation`` — and the browser shows exactly that layer. The last command is
cached and re-sent whenever a client (re)connects, so a browser refresh or a
dropped socket always resyncs to the current state.

The browser may push events back (``room_joined`` / ``room_ended``) when it uses
the Daily SDK; these are forwarded to an injected async handler.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger("kiosk.frontend")

EventHandler = Callable[[str, dict], Awaitable[None]]


class FrontendLink:
    def __init__(self, host: str, port: int, *, on_event: EventHandler | None = None) -> None:
        self.host = host
        self.port = port
        self._on_event = on_event
        self._clients: set[WebSocketServerProtocol] = set()
        self._current: dict = {"cmd": "attract"}
        self._server: websockets.WebSocketServer | None = None

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info("Frontend WebSocket listening on ws://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handler(self, ws: WebSocketServerProtocol) -> None:
        self._clients.add(ws)
        logger.info("Frontend connected (%d total)", len(self._clients))
        try:
            # Resync the newcomer to the current state immediately.
            await ws.send(json.dumps(self._current))
            async for raw in ws:
                await self._on_message(raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            logger.info("Frontend disconnected (%d total)", len(self._clients))

    async def _on_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("Ignoring non-JSON frontend message: %r", raw[:120])
            return
        event = msg.get("event")
        if event and self._on_event is not None:
            await self._on_event(event, msg)

    async def _broadcast(self, payload: dict) -> None:
        self._current = payload
        if not self._clients:
            return
        data = json.dumps(payload)
        results = await asyncio.gather(
            *(client.send(data) for client in list(self._clients)),
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, Exception):
                logger.debug("Send to a client failed: %s", res)

    # -- command helpers (match state_machine.Callbacks) ---------------------
    async def show_attract(self) -> None:
        await self._broadcast({"cmd": "attract"})

    async def show_greeting(self) -> None:
        await self._broadcast({"cmd": "greeting"})

    async def show_conversation(self, url: str) -> None:
        await self._broadcast({"cmd": "conversation", "url": url})
