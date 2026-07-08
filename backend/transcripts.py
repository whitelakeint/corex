"""Transcript normalisation + "the bot couldn't answer" detection.

Pure functions — no database, no network — so they are cheap to unit-test.

Detection is deliberately deterministic (no LLM): we look for the bot's own
*indications* that it couldn't help. The concierge persona emits a small set of
canned phrases when it hits its limits (e.g. "a member of our team would be
better suited…" right before it escalates), plus generic hedges like "I'm not
sure". Each such assistant turn is paired with the visitor turn that preceded it
— that visitor question becomes an "unanswered question" for expert review.

The phrase list is seeded here but is admin-tunable in the DB
(``deflection_phrases`` table), so experts can refine what counts as a miss.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# Default signals the bot couldn't answer. Kept in sync with the escalation
# phrases in scripts/setup_persona.py. Seeded into deflection_phrases.
DEFAULT_DEFLECTION_PHRASES: list[str] = [
    "a member of our team would be better suited",
    "let me connect you with someone",
    "i've set up a video call",
    "connect you to a real person",
    "connecting you to a staff member",
    "i'm not sure",
    "i am not sure",
    "i don't have that information",
    "i do not have that information",
    "i don't know",
    "i'm not able to help with that",
    "i can't help with that",
    "i'm unable to help with that",
]

_VISITOR_ROLES = {"visitor", "user", "customer", "human", "guest", "caller"}
_ASSISTANT_ROLES = {"assistant", "replica", "agent", "bot", "ai", "concierge", "system"}


@dataclass
class Turn:
    turn_index: int
    role: str          # normalised: 'visitor' | 'assistant'
    content: str
    spoken_at: str | None = None


@dataclass
class Phrase:
    phrase: str
    match_type: str = "contains"   # 'contains' | 'regex'


@dataclass
class UnansweredDetection:
    question: str
    matched_phrase: str
    source: str                    # 'deflection_phrase'
    context_excerpt: str
    assistant_turn_index: int
    visitor_turn_index: int | None = None
    tags: list[str] = field(default_factory=list)


def normalize_role(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower()
    if key in _VISITOR_ROLES:
        return "visitor"
    if key in _ASSISTANT_ROLES:
        return "assistant"
    return None


def normalize_transcript(source) -> list[Turn]:
    """Accepts a Tavus webhook payload, a ``properties.transcript`` value, a list
    of turn dicts, or a plain string, and returns an ordered list of Turns.
    Unknown roles are dropped (we only reason about visitor<->assistant pairs).
    """
    transcript = source
    if isinstance(source, dict):
        # Full webhook payload or a nested properties object.
        props = source.get("properties", source)
        transcript = props.get("transcript", props.get("messages", source.get("transcript")))

    turns: list[Turn] = []

    if isinstance(transcript, list):
        idx = 0
        for item in transcript:
            if not isinstance(item, dict):
                continue
            role = normalize_role(
                item.get("role") or item.get("speaker") or item.get("from")
            )
            content = (
                item.get("content")
                or item.get("text")
                or item.get("message")
                or ""
            )
            content = str(content).strip()
            if role is None or not content:
                continue
            turns.append(Turn(turn_index=idx, role=role,
                              content=content, spoken_at=item.get("timestamp")))
            idx += 1
        return turns

    if isinstance(transcript, str) and transcript.strip():
        # Fall back to "Role: text" line parsing.
        idx = 0
        for line in transcript.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            speaker, _, text = line.partition(":")
            role = normalize_role(speaker)
            text = text.strip()
            if role is None or not text:
                continue
            turns.append(Turn(turn_index=idx, role=role, content=text))
            idx += 1
        return turns

    return turns


def _matches(text: str, phrase: Phrase) -> bool:
    if not text:
        return False
    if phrase.match_type == "regex":
        try:
            return re.search(phrase.phrase, text, re.IGNORECASE) is not None
        except re.error:
            return False
    return phrase.phrase.lower() in text.lower()


def detect_unanswered(
    turns: list[Turn],
    phrases: list[Phrase] | None = None,
) -> list[UnansweredDetection]:
    """Pair each deflecting assistant turn with the visitor question before it."""
    if phrases is None:
        phrases = [Phrase(p) for p in DEFAULT_DEFLECTION_PHRASES]

    results: list[UnansweredDetection] = []
    last_visitor: Turn | None = None

    for turn in turns:
        if turn.role == "visitor":
            last_visitor = turn
            continue
        if turn.role != "assistant":
            continue
        for phrase in phrases:
            if _matches(turn.content, phrase):
                if last_visitor is None:
                    break  # no question to attribute the miss to
                results.append(
                    UnansweredDetection(
                        question=last_visitor.content,
                        matched_phrase=phrase.phrase,
                        source="deflection_phrase",
                        context_excerpt=_excerpt(last_visitor, turn),
                        assistant_turn_index=turn.turn_index,
                        visitor_turn_index=last_visitor.turn_index,
                    )
                )
                last_visitor = None  # don't double-count the same question
                break

    return results


def _excerpt(visitor: Turn, assistant: Turn) -> str:
    return f"Visitor: {visitor.content}\nConcierge: {assistant.content}"


def dedup_hash(bot_id: int | str, question: str) -> str:
    """Stable hash so the same unanswered question isn't queued twice per bot."""
    norm = re.sub(r"\s+", " ", question.strip().lower())
    return hashlib.sha1(f"{bot_id}:{norm}".encode("utf-8")).hexdigest()
