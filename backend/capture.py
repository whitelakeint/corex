"""Capture orchestration: turn a Tavus transcript into stored records.

Called from the ``application.transcription_ready`` webhook (and the manual
ingest endpoint). Everything here is best-effort — a DB outage logs a warning
and returns, it never breaks the webhook response or the live conversation.
"""

from __future__ import annotations

import datetime as _dt
import logging

from backend import db
from backend.config import BOT_ID, BOT_NAME, CAPTURE_ENABLED, PROPERTY_NAME
from backend.transcripts import detect_unanswered, normalize_transcript

logger = logging.getLogger("concierge.capture")


def _parse_ts(value) -> _dt.datetime | None:
    if not value:
        return None
    if isinstance(value, _dt.datetime):
        return value
    try:
        return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def record_conversation_started(tavus_conversation_id: str, *, source: str) -> None:
    """Record a conversation the moment it's created (manual or kiosk)."""
    if not CAPTURE_ENABLED or not tavus_conversation_id:
        return
    try:
        engine = db.get_engine()
        with engine.begin() as conn:
            bot_id = db.ensure_bot(conn, BOT_ID, BOT_NAME, PROPERTY_NAME)
            db.upsert_conversation(
                conn, bot_id=bot_id, tavus_conversation_id=tavus_conversation_id,
                source=source, status="active", started_at=db._now(),
            )
        logger.info("Recorded conversation start %s (bot=%s)", tavus_conversation_id, BOT_ID)
    except Exception as exc:  # noqa: BLE001
        logger.warning("record_conversation_started failed: %s", exc)


def ingest_transcript(payload: dict) -> dict:
    """Store the transcript and queue any unanswered questions.

    ``payload`` is the Tavus webhook body (or an equivalent dict with a
    ``conversation_id`` and ``properties.transcript``). Returns a small summary.
    """
    summary = {"stored_messages": 0, "unanswered_new": 0, "conversation_id": None}
    if not CAPTURE_ENABLED:
        return summary

    props = payload.get("properties", {}) if isinstance(payload, dict) else {}
    tavus_conversation_id = (
        payload.get("conversation_id")
        or props.get("conversation_id")
        or ""
    )
    if not tavus_conversation_id:
        logger.warning("ingest_transcript: no conversation_id in payload")
        return summary

    turns = normalize_transcript(payload)
    raw = props.get("transcript")
    raw_text = raw if isinstance(raw, str) else None

    started = _parse_ts(props.get("started_at") or payload.get("started_at"))
    ended = _parse_ts(props.get("ended_at") or payload.get("ended_at")) or db._now()
    duration = None
    if started and ended:
        duration = int((ended - started).total_seconds())

    try:
        engine = db.get_engine()
        with engine.begin() as conn:
            bot_id = db.ensure_bot(conn, BOT_ID, BOT_NAME, PROPERTY_NAME)
            conv_id = db.upsert_conversation(
                conn, bot_id=bot_id, tavus_conversation_id=tavus_conversation_id,
                status="ended", started_at=started, ended_at=ended,
                duration_seconds=duration, raw_transcript=raw_text,
            )
            summary["conversation_id"] = conv_id
            summary["stored_messages"] = db.replace_messages(conn, conv_id, turns)

            phrases = db.active_phrases(conn, bot_id)
            detections = detect_unanswered(turns, phrases or None)
            new = 0
            for det in detections:
                if db.insert_unanswered(conn, bot_id=bot_id, conversation_id=conv_id, detection=det):
                    new += 1
            summary["unanswered_new"] = new

        logger.info(
            "Ingested transcript %s: %d messages, %d new unanswered",
            tavus_conversation_id, summary["stored_messages"], summary["unanswered_new"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ingest_transcript failed for %s: %s", tavus_conversation_id, exc)

    return summary
