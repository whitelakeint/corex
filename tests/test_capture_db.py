"""Repository + capture orchestration against an in-memory SQLite DB."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, insert, select

from backend import capture, db
from backend.transcripts import Turn, UnansweredDetection


@pytest.fixture()
def engine(monkeypatch):
    eng = create_engine("sqlite://", future=True)
    db.init_schema(eng)
    # Point the whole module (and capture.py, which calls db.get_engine) at it.
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "get_engine", lambda: eng)
    return eng


def test_ensure_bot_is_idempotent(engine):
    with engine.begin() as conn:
        a = db.ensure_bot(conn, "meridian-01", "Meridian Lobby", "The Meridian")
        b = db.ensure_bot(conn, "meridian-01", "Meridian Lobby", "The Meridian")
    assert a == b


def test_upsert_conversation_insert_then_update(engine):
    with engine.begin() as conn:
        bot = db.ensure_bot(conn, "b", "B", "B")
        cid = db.upsert_conversation(conn, bot_id=bot, tavus_conversation_id="c1",
                                     source="manual", status="active")
        cid2 = db.upsert_conversation(conn, bot_id=bot, tavus_conversation_id="c1",
                                      status="ended", duration_seconds=42)
    assert cid == cid2
    with engine.connect() as conn:
        row = conn.execute(select(db.conversations.c.status,
                                  db.conversations.c.duration_seconds)
                           .where(db.conversations.c.id == cid)).first()
    assert row[0] == "ended" and row[1] == 42


def test_replace_messages_is_idempotent(engine):
    with engine.begin() as conn:
        bot = db.ensure_bot(conn, "b", "B", "B")
        cid = db.upsert_conversation(conn, bot_id=bot, tavus_conversation_id="c1")
        db.replace_messages(conn, cid, [Turn(0, "visitor", "hi"), Turn(1, "assistant", "hello")])
        n = db.replace_messages(conn, cid, [Turn(0, "visitor", "hi again")])
    assert n == 1
    with engine.connect() as conn:
        rows = conn.execute(select(db.transcript_messages.c.content)
                            .where(db.transcript_messages.c.conversation_id == cid)).all()
    assert [r[0] for r in rows] == ["hi again"]


def test_active_phrases_global_and_bot_specific(engine):
    with engine.begin() as conn:
        bot = db.ensure_bot(conn, "b", "B", "B")
        other = db.ensure_bot(conn, "b2", "B2", "B2")
        conn.execute(insert(db.deflection_phrases), [
            {"bot_id": None, "phrase": "i'm not sure", "match_type": "contains", "active": True},
            {"bot_id": bot, "phrase": "no clue", "match_type": "contains", "active": True},
            {"bot_id": bot, "phrase": "disabled", "match_type": "contains", "active": False},
            {"bot_id": other, "phrase": "other-bot", "match_type": "contains", "active": True},
        ])
        phrases = db.active_phrases(conn, bot)
    got = {p.phrase for p in phrases}
    assert got == {"i'm not sure", "no clue"}  # global + this bot, active only


def test_insert_unanswered_dedups(engine):
    det = UnansweredDetection(question="Where is the gym?", matched_phrase="i'm not sure",
                              source="deflection_phrase", context_excerpt="...",
                              assistant_turn_index=1, visitor_turn_index=0)
    with engine.begin() as conn:
        bot = db.ensure_bot(conn, "b", "B", "B")
        first = db.insert_unanswered(conn, bot_id=bot, conversation_id=None, detection=det)
        dup = db.insert_unanswered(conn, bot_id=bot, conversation_id=None, detection=det)
    assert first is True and dup is False


def test_ingest_transcript_end_to_end(engine):
    payload = {
        "event_type": "application.transcription_ready",
        "conversation_id": "conv-xyz",
        "properties": {"transcript": [
            {"role": "user", "content": "Where is the pool?"},
            {"role": "assistant", "content": "The pool is on the 3rd floor."},
            {"role": "user", "content": "Can you waive my late fee?"},
            {"role": "assistant", "content": "I'm not sure, a member of our team would be better suited."},
        ]},
    }
    summary = capture.ingest_transcript(payload)
    assert summary["stored_messages"] == 4
    assert summary["unanswered_new"] == 1
    with engine.connect() as conn:
        q = conn.execute(select(db.unanswered_questions.c.question,
                                db.unanswered_questions.c.status)).all()
    assert len(q) == 1
    assert q[0][0] == "Can you waive my late fee?"
    assert q[0][1] == "pending"


def test_ingest_transcript_is_reingest_safe(engine):
    payload = {
        "conversation_id": "conv-1",
        "properties": {"transcript": [
            {"role": "user", "content": "Pets allowed?"},
            {"role": "assistant", "content": "I don't have that information."},
        ]},
    }
    capture.ingest_transcript(payload)
    capture.ingest_transcript(payload)  # replay same webhook
    with engine.connect() as conn:
        msgs = conn.execute(select(db.transcript_messages.c.id)).all()
        uq = conn.execute(select(db.unanswered_questions.c.id)).all()
    assert len(msgs) == 2   # messages replaced, not duplicated
    assert len(uq) == 1     # question deduped
