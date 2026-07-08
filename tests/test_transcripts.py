"""Transcript normalisation + unanswered-question detection (pure functions)."""

from __future__ import annotations

from backend.transcripts import (
    Phrase,
    Turn,
    dedup_hash,
    detect_unanswered,
    normalize_transcript,
)


def test_normalize_list_of_role_content():
    turns = normalize_transcript([
        {"role": "user", "content": "Where is the gym?"},
        {"role": "replica", "content": "The gym is on the 2nd floor."},
    ])
    assert [t.role for t in turns] == ["visitor", "assistant"]
    assert turns[0].content == "Where is the gym?"
    assert turns[0].turn_index == 0 and turns[1].turn_index == 1


def test_normalize_speaker_text_and_unknown_roles_dropped():
    turns = normalize_transcript([
        {"speaker": "customer", "text": "Hi"},
        {"speaker": "system-note", "text": "ignored"},
        {"speaker": "agent", "text": "Hello!"},
    ])
    assert [t.role for t in turns] == ["visitor", "assistant"]


def test_normalize_webhook_payload_shape():
    payload = {
        "event_type": "application.transcription_ready",
        "conversation_id": "c1",
        "properties": {"transcript": [
            {"role": "user", "content": "Do you allow pets?"},
            {"role": "assistant", "content": "I'm not sure about that."},
        ]},
    }
    turns = normalize_transcript(payload)
    assert len(turns) == 2 and turns[1].content == "I'm not sure about that."


def test_normalize_plain_string():
    turns = normalize_transcript("User: hello\nAssistant: hi there")
    assert [t.role for t in turns] == ["visitor", "assistant"]


def test_detect_pairs_question_with_deflection():
    turns = [
        Turn(0, "visitor", "Do you allow pets on the balcony?"),
        Turn(1, "assistant", "I'm not sure about that, let me check."),
    ]
    dets = detect_unanswered(turns)
    assert len(dets) == 1
    assert dets[0].question == "Do you allow pets on the balcony?"
    assert dets[0].source == "deflection_phrase"
    assert "not sure" in dets[0].matched_phrase


def test_detect_uses_escalation_canned_phrase():
    turns = [
        Turn(0, "visitor", "Can you change my lease terms?"),
        Turn(1, "assistant",
             "That's a great question, but a member of our team would be better suited to help."),
    ]
    dets = detect_unanswered(turns)
    assert len(dets) == 1
    assert dets[0].question.startswith("Can you change my lease")


def test_detect_no_false_positive_on_normal_answer():
    turns = [
        Turn(0, "visitor", "Where is the pool?"),
        Turn(1, "assistant", "The pool is on the 3rd floor, open 6am to 10pm."),
    ]
    assert detect_unanswered(turns) == []


def test_detect_ignores_deflection_with_no_preceding_question():
    turns = [Turn(0, "assistant", "I'm not sure.")]
    assert detect_unanswered(turns) == []


def test_detect_does_not_double_count_same_question():
    turns = [
        Turn(0, "visitor", "What's the wifi password?"),
        Turn(1, "assistant", "I'm not sure, I don't have that information."),
    ]
    # Two phrases match the one assistant turn, but the question is queued once.
    assert len(detect_unanswered(turns)) == 1


def test_detect_custom_phrase_list_and_regex():
    turns = [
        Turn(0, "visitor", "Refund policy?"),
        Turn(1, "assistant", "Please contact the office for that."),
    ]
    dets = detect_unanswered(turns, [Phrase(r"contact the .*office", "regex")])
    assert len(dets) == 1


def test_dedup_hash_normalises_whitespace_and_case():
    assert dedup_hash(1, "Where is the GYM?") == dedup_hash(1, "  where   is the gym? ")
    assert dedup_hash(1, "x") != dedup_hash(2, "x")  # per-bot
