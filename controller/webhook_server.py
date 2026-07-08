"""OPTIONAL Tavus webhook receiver.

Only useful when ``tavus.callback_url`` is a **publicly reachable** URL. Kiosks
behind NAT can't receive callbacks — in that case skip this entirely and rely on
the frontend Daily ``room_ended`` event, the ``GET`` status poll, and Tavus's
own ``participant_left_timeout`` / ``max_call_duration`` backstops.

If you do have a public URL, run this alongside the controller and point
``callback_url`` at it. It exposes ``POST /webhooks/tavus`` and invokes injected
callbacks so the controller can react to server-side room shutdowns.

    from controller.webhook_server import create_webhook_app
    app = create_webhook_app(on_shutdown=my_async_handler)
    # serve with: uvicorn.run(app, host="0.0.0.0", port=8080)
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request

logger = logging.getLogger("kiosk.webhook")

AsyncHandler = Callable[[dict], Awaitable[None]]


async def _noop(_payload: dict) -> None:  # pragma: no cover - default
    return None


def create_webhook_app(
    *,
    on_replica_joined: AsyncHandler = _noop,
    on_shutdown: AsyncHandler = _noop,
    on_transcription: AsyncHandler = _noop,
) -> FastAPI:
    app = FastAPI(title="Kiosk Tavus Webhook Receiver")

    @app.post("/webhooks/tavus")
    async def tavus_webhook(request: Request) -> dict:
        payload = await request.json()
        event_type = payload.get("event_type", "unknown")
        logger.info("Webhook: %s", event_type)

        if event_type == "system.replica_joined":
            # Replica is live; safe to reveal the room.
            await on_replica_joined(payload)
        elif event_type == "system.shutdown":
            # Room closed server-side (e.g. hit max_call_duration).
            reason = payload.get("properties", {}).get("shutdown_reason", "")
            logger.info("system.shutdown reason=%s", reason)
            await on_shutdown(payload)
        elif event_type == "application.transcription_ready":
            await on_transcription(payload)

        return {"status": "ok"}

    return app
