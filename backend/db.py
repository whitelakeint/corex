"""Database layer for transcript / knowledge-base capture.

SQLAlchemy Core tables that MIRROR the Laravel admin's migrations (which remain
the schema source of truth — see admin/database/migrations and db/schema.sql).
The Python runtime only *writes* capture data (conversations, transcripts,
unanswered questions) and *reads* the admin-tuned deflection phrases; the expert
answer / approval / publish workflow lives entirely in the Laravel app.

All types are generic so the same definitions run against MySQL in production
and SQLite in the unit tests.
"""

from __future__ import annotations

import datetime as _dt
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Connection, Engine

from backend.config import DATABASE_URL
from backend.transcripts import Phrase, Turn, UnansweredDetection, dedup_hash

logger = logging.getLogger("concierge.db")

metadata = MetaData()


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


bots = Table(
    "bots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("slug", String(120), unique=True, nullable=False),
    Column("name", String(190), nullable=False),
    Column("property_name", String(190), nullable=True),
    Column("address", String(255), nullable=True),
    Column("tavus_persona_id", String(120), nullable=True),
    Column("tavus_replica_id", String(120), nullable=True),
    Column("kb_base_context", Text, nullable=True),
    Column("active", Boolean, default=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("bot_id", Integer, ForeignKey("bots.id"), nullable=False),
    Column("tavus_conversation_id", String(120), unique=True, nullable=False),
    Column("source", String(40), nullable=True),        # kiosk | manual
    Column("status", String(40), nullable=True),        # active | ended
    Column("started_at", DateTime, nullable=True),
    Column("ended_at", DateTime, nullable=True),
    Column("duration_seconds", Integer, nullable=True),
    Column("raw_transcript", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

transcript_messages = Table(
    "transcript_messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", Integer, ForeignKey("conversations.id"), nullable=False),
    Column("turn_index", Integer, nullable=False),
    Column("role", String(20), nullable=False),         # visitor | assistant
    Column("content", Text, nullable=False),
    Column("spoken_at", String(64), nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

deflection_phrases = Table(
    "deflection_phrases",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("bot_id", Integer, ForeignKey("bots.id"), nullable=True),  # null = global
    Column("phrase", String(255), nullable=False),
    Column("match_type", String(20), default="contains"),  # contains | regex
    Column("active", Boolean, default=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

unanswered_questions = Table(
    "unanswered_questions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("bot_id", Integer, ForeignKey("bots.id"), nullable=False),
    Column("conversation_id", Integer, ForeignKey("conversations.id"), nullable=True),
    Column("question", Text, nullable=False),
    Column("context_excerpt", Text, nullable=True),
    Column("source", String(40), nullable=False),          # deflection_phrase | escalation
    Column("matched_phrase", String(255), nullable=True),
    Column("status", String(40), default="pending"),       # pending|answered|approved|rejected|published
    Column("dedup_hash", String(64), nullable=False),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    UniqueConstraint("bot_id", "dedup_hash", name="uq_unanswered_bot_dedup"),
)

# Defined here for completeness / SQLite tests; owned + written by the Laravel admin.
knowledge_answers = Table(
    "knowledge_answers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("unanswered_question_id", Integer, ForeignKey("unanswered_questions.id"), nullable=True),
    Column("bot_id", Integer, ForeignKey("bots.id"), nullable=False),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("authored_by", String(190), nullable=True),
    Column("status", String(40), default="draft"),  # draft|pending_approval|approved|rejected|published
    Column("reviewed_by", String(190), nullable=True),
    Column("reject_reason", String(255), nullable=True),
    Column("approved_at", DateTime, nullable=True),
    Column("published_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    return _engine


def is_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(select(1))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Capture DB unavailable: %s", exc)
        return False


def init_schema(engine: Engine) -> None:
    """Create tables. Used for SQLite tests / first-run bootstrap only — in
    production the Laravel migrations own the schema."""
    metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Repository (all take an open Connection so a whole ingest is one transaction)
# ---------------------------------------------------------------------------
def ensure_bot(conn: Connection, slug: str, name: str, property_name: str | None) -> int:
    row = conn.execute(select(bots.c.id).where(bots.c.slug == slug)).first()
    if row:
        return row[0]
    now = _now()
    result = conn.execute(
        insert(bots).values(
            slug=slug, name=name, property_name=property_name,
            active=True, created_at=now, updated_at=now,
        )
    )
    return int(result.inserted_primary_key[0])


def upsert_conversation(conn: Connection, *, bot_id: int, tavus_conversation_id: str,
                        source: str | None = None, status: str | None = None,
                        started_at=None, ended_at=None, duration_seconds: int | None = None,
                        raw_transcript: str | None = None) -> int:
    row = conn.execute(
        select(conversations.c.id).where(
            conversations.c.tavus_conversation_id == tavus_conversation_id
        )
    ).first()
    now = _now()
    values = {
        "source": source, "status": status, "started_at": started_at,
        "ended_at": ended_at, "duration_seconds": duration_seconds,
        "raw_transcript": raw_transcript, "updated_at": now,
    }
    # Drop None values so an update never clobbers existing data with NULL.
    values = {k: v for k, v in values.items() if v is not None}

    if row:
        if values:
            conn.execute(update(conversations).where(conversations.c.id == row[0]).values(**values))
        return int(row[0])

    result = conn.execute(
        insert(conversations).values(
            bot_id=bot_id, tavus_conversation_id=tavus_conversation_id,
            created_at=now, **values,
        )
    )
    return int(result.inserted_primary_key[0])


def replace_messages(conn: Connection, conversation_id: int, turns: list[Turn]) -> int:
    """Re-ingest safe: clears prior turns for this conversation, then inserts."""
    conn.execute(delete(transcript_messages).where(
        transcript_messages.c.conversation_id == conversation_id
    ))
    if not turns:
        return 0
    now = _now()
    conn.execute(
        insert(transcript_messages),
        [
            {
                "conversation_id": conversation_id,
                "turn_index": t.turn_index,
                "role": t.role,
                "content": t.content,
                "spoken_at": t.spoken_at,
                "created_at": now,
                "updated_at": now,
            }
            for t in turns
        ],
    )
    return len(turns)


def active_phrases(conn: Connection, bot_id: int) -> list[Phrase]:
    rows = conn.execute(
        select(deflection_phrases.c.phrase, deflection_phrases.c.match_type).where(
            deflection_phrases.c.active.is_(True),
            (deflection_phrases.c.bot_id == bot_id) | (deflection_phrases.c.bot_id.is_(None)),
        )
    ).all()
    return [Phrase(phrase=r[0], match_type=r[1] or "contains") for r in rows]


def insert_unanswered(conn: Connection, *, bot_id: int, conversation_id: int | None,
                      detection: UnansweredDetection) -> bool:
    """Insert one unanswered question. Returns False if it's a duplicate."""
    dh = dedup_hash(bot_id, detection.question)
    exists = conn.execute(
        select(unanswered_questions.c.id).where(
            unanswered_questions.c.bot_id == bot_id,
            unanswered_questions.c.dedup_hash == dh,
        )
    ).first()
    if exists:
        return False
    now = _now()
    conn.execute(
        insert(unanswered_questions).values(
            bot_id=bot_id, conversation_id=conversation_id,
            question=detection.question, context_excerpt=detection.context_excerpt,
            source=detection.source, matched_phrase=detection.matched_phrase,
            status="pending", dedup_hash=dh, created_at=now, updated_at=now,
        )
    )
    return True
