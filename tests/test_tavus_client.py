"""Tavus client wrapper tests — create body, retry/backoff, idempotent end."""

from __future__ import annotations

import asyncio

import httpx

from controller import tavus_client as tc
from controller.config import Config


def _cfg() -> Config:
    cfg = Config()
    cfg.tavus.persona_id = "p123"
    cfg.tavus.replica_id = "r123"
    cfg.property.name = "Test Tower"
    return cfg


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://tavusapi.com/v2/conversations")
    response = httpx.Response(status_code=status, request=request, text="err")
    return httpx.HTTPStatusError("boom", request=request, response=response)


def _run(coro):
    return asyncio.run(coro)


def test_create_builds_kiosk_body(monkeypatch):
    captured = {}

    async def fake_create(persona_id, **kwargs):
        captured["persona_id"] = persona_id
        captured.update(kwargs)
        return {"conversation_id": "c1", "conversation_url": "https://room", "status": "active"}

    monkeypatch.setattr(tc._api, "create_conversation", fake_create)

    client = tc.TavusClient(_cfg(), backoff_base_s=0)
    data = _run(client.create("kiosk-test"))

    assert data["conversation_url"] == "https://room"
    assert captured["persona_id"] == "p123"
    assert captured["replica_id"] == "r123"
    assert captured["conversation_name"] == "kiosk-test"
    assert "Test Tower" in captured["conversational_context"]
    props = captured["properties"]
    assert props["max_call_duration"] == 600
    assert props["enable_recording"] is False


def test_create_retries_on_5xx_then_succeeds(monkeypatch):
    calls = {"n": 0}

    async def flaky_create(persona_id, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(503)
        return {"conversation_id": "c1", "conversation_url": "https://room"}

    monkeypatch.setattr(tc._api, "create_conversation", flaky_create)

    client = tc.TavusClient(_cfg(), max_retries=3, backoff_base_s=0)
    data = _run(client.create("kiosk-test"))

    assert calls["n"] == 2
    assert data["conversation_id"] == "c1"


def test_create_gives_up_on_4xx(monkeypatch):
    async def bad_create(persona_id, **kwargs):
        raise _http_error(400)

    monkeypatch.setattr(tc._api, "create_conversation", bad_create)

    client = tc.TavusClient(_cfg(), max_retries=2, backoff_base_s=0)
    raised = False
    try:
        _run(client.create("kiosk-test"))
    except httpx.HTTPStatusError:
        raised = True
    assert raised is True


def test_end_is_idempotent_on_404(monkeypatch):
    async def not_found_end(conversation_id):
        raise _http_error(404)

    monkeypatch.setattr(tc._api, "end_conversation", not_found_end)

    client = tc.TavusClient(_cfg())
    result = _run(client.end("c1"))
    assert result["status"] == "already_ended"


def test_end_never_raises(monkeypatch):
    async def boom_end(conversation_id):
        raise RuntimeError("network gone")

    monkeypatch.setattr(tc._api, "end_conversation", boom_end)

    client = tc.TavusClient(_cfg())
    result = _run(client.end("c1"))  # must not raise
    assert result["status"] == "error"


def test_end_noop_on_empty_id():
    client = tc.TavusClient(_cfg())
    result = _run(client.end(""))
    assert result["status"] == "noop"


def test_get_delegates(monkeypatch):
    async def fake_get(conversation_id):
        return {"conversation_id": conversation_id, "status": "ended"}

    monkeypatch.setattr(tc._api, "get_conversation", fake_get)

    client = tc.TavusClient(_cfg(), backoff_base_s=0)
    data = _run(client.get("c1"))
    assert data["status"] == "ended"
