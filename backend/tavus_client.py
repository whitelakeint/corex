from __future__ import annotations

import httpx

from backend.config import TAVUS_API_KEY

BASE_URL = "https://tavusapi.com/v2"

_headers = {
    "x-api-key": TAVUS_API_KEY,
    "Content-Type": "application/json",
}


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, headers=_headers, timeout=120.0)


async def create_persona(payload: dict) -> dict:
    async with await _client() as client:
        resp = await client.post("/personas", json=payload)
        if resp.status_code >= 400:
            print(f"Tavus API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()


async def create_conversation(persona_id: str, **kwargs) -> dict:
    body = {"persona_id": persona_id, **kwargs}
    async with await _client() as client:
        resp = await client.post("/conversations", json=body)
        if resp.status_code >= 400:
            print(f"Tavus API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()


async def upload_document(name: str, url: str, tags: list[str]) -> dict:
    body = {"name": name, "url": url, "tags": tags}
    async with await _client() as client:
        resp = await client.post("/documents", json=body)
        resp.raise_for_status()
        return resp.json()


async def get_document(document_id: str) -> dict:
    async with await _client() as client:
        resp = await client.get(f"/documents/{document_id}")
        resp.raise_for_status()
        return resp.json()


async def list_conversations() -> dict:
    async with await _client() as client:
        resp = await client.get("/conversations")
        resp.raise_for_status()
        return resp.json()


async def get_conversation(conversation_id: str) -> dict:
    """Fetch a single conversation's current status/details."""
    async with await _client() as client:
        resp = await client.get(f"/conversations/{conversation_id}")
        if resp.status_code >= 400:
            print(f"Tavus API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()


async def patch_persona(persona_id: str, operations: list[dict]) -> dict:
    async with await _client() as client:
        resp = await client.patch(f"/personas/{persona_id}", json=operations)
        if resp.status_code >= 400:
            print(f"Tavus API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.json()


async def end_conversation(conversation_id: str) -> dict:
    async with await _client() as client:
        resp = await client.post(f"/conversations/{conversation_id}/end")
        resp.raise_for_status()
        # Handle empty or non-JSON responses (Tavus returns 200 with empty body)
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok", "conversation_id": conversation_id}
        try:
            return resp.json()
        except Exception:
            return {"status": "ok", "conversation_id": conversation_id}
