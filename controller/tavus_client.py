"""Kiosk-facing Tavus client.

Thin async wrapper over :mod:`backend.tavus_client` (shared with the web
backend) that adds the three behaviours the presence controller needs:

* a kiosk-shaped **create** call (replica + persona + context + backstops),
* **retry with backoff** on transient 5xx / network errors,
* an **idempotent end** that treats "already ended / not found" as success.

Every open room costs money, so ``end`` is deliberately forgiving: it never
raises, guaranteeing the controller can always fire-and-forget a teardown.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from backend import tavus_client as _api
from controller.config import Config

logger = logging.getLogger("kiosk.tavus")

_RETRYABLE_STATUS = {500, 502, 503, 504, 429}


class TavusClient:
    def __init__(self, cfg: Config, *, max_retries: int = 3, backoff_base_s: float = 1.0) -> None:
        self.cfg = cfg
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s

    async def _with_retry(self, label: str, coro_factory):
        attempt = 0
        while True:
            try:
                return await coro_factory()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in _RETRYABLE_STATUS and attempt < self.max_retries:
                    delay = self.backoff_base_s * (2 ** attempt)
                    logger.warning("%s got %s, retry %d in %.1fs", label, status, attempt + 1, delay)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                logger.error("%s failed (%s): %s", label, status, exc.response.text[:200])
                raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_base_s * (2 ** attempt)
                    logger.warning("%s transport error, retry %d in %.1fs: %s", label, attempt + 1, delay, exc)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                logger.error("%s failed after retries: %s", label, exc)
                raise

    async def create(self, conversation_name: str) -> dict:
        """Create a kiosk conversation. Returns the raw Tavus response
        (``conversation_id``, ``conversation_url``, ``status``)."""
        t = self.cfg.tavus
        kwargs: dict = {
            "replica_id": t.replica_id,
            "conversation_name": conversation_name,
            "conversational_context": self.cfg.property.context(),
            "properties": {
                "max_call_duration": t.max_call_duration,
                "participant_left_timeout": t.participant_left_timeout,
                "participant_absent_timeout": t.participant_absent_timeout,
                "enable_recording": t.enable_recording,
            },
        }
        if t.callback_url:
            kwargs["callback_url"] = t.callback_url

        return await self._with_retry(
            "create_conversation",
            lambda: _api.create_conversation(persona_id=t.persona_id, **kwargs),
        )

    async def get(self, conversation_id: str) -> dict:
        return await self._with_retry(
            "get_conversation",
            lambda: _api.get_conversation(conversation_id),
        )

    async def end(self, conversation_id: str) -> dict:
        """Idempotent teardown — never raises so callers can fire-and-forget."""
        if not conversation_id:
            return {"status": "noop"}
        try:
            result = await _api.end_conversation(conversation_id)
            logger.info("Ended conversation %s", conversation_id)
            return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (404, 400, 409):
                logger.info("Conversation %s already ended (%s)", conversation_id, exc.response.status_code)
                return {"status": "already_ended", "conversation_id": conversation_id}
            logger.error("End failed for %s: %s", conversation_id, exc)
            return {"status": "error", "conversation_id": conversation_id}
        except Exception as exc:  # noqa: BLE001 - teardown must never crash the loop
            logger.error("End errored for %s: %s", conversation_id, exc)
            return {"status": "error", "conversation_id": conversation_id}
