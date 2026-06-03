# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A real-time AI building concierge avatar for "The Meridian" luxury residential building, powered by Tavus.io's Conversational Video Interface (CVI). A FastAPI backend manages conversation lifecycle and tool execution (currently stubbed for demo). A single-page web portal embeds the Tavus avatar via iframe over WebRTC.

## Architecture

```
Browser (frontend/index.html)
  → POST /api/conversations → FastAPI backend
  → receives conversation_url → loads in iframe (WebRTC to Tavus)
  → Tavus CVI handles STT/LLM/TTS/Avatar rendering
  → LLM tool calls → Tavus webhooks → POST /webhooks/tavus on backend
  → stub handlers log to console, return simulated responses
```

The Tavus persona (created via `scripts/setup_persona.py`) defines the avatar's behavior through a system prompt encoding 9 Q&A categories (visitor ID, access, leasing, directions, packages, amenities, safety, escalation, closing) and 5 tool definitions (notify_resident, unlock_door, schedule_tour, notify_management, log_delivery).

## Multi-User Support

The application supports multiple users with separate avatars and knowledge bases:

**Users:**
- `admin` - Meridian Building (default)
- `buildingB` - Building B

**Configuration:**
Users are defined in `backend/config.py` USERS dict. Each user has:
- Password (both use "meridian")
- Tavus persona_id (different avatar)
- Tavus replica_id (different appearance)
- KB directory path (separate content)

**Login:**
- Dropdown selection on login screen
- Username auto-filled based on selection
- SessionStorage persists user selection

**Conversation Flow:**
- Frontend sends `username` in POST /api/conversations
- Backend looks up user's persona_id
- Creates conversation with user-specific Tavus persona

**KB Management:**
- KB page detects user from URL param: `/admin/knowledge-base?user=buildingB`
- Load/save/sync operations target user-specific KB directory
- Complete isolation between users

**Creating New User Personas:**
```bash
# Create persona for a user
python -m scripts.setup_persona --user buildingB --replica <replica_id>

# Copy returned persona_id to .env
BUILDINGB_PERSONA_ID=<persona_id>
```

**Adding New Users:**
1. Add entry to USERS dict in `backend/config.py`
2. Create KB directory: `knowledge-base/<username>/`
3. Add persona/replica env vars to `.env`
4. Run `setup_persona.py` with new user
5. Add option to login dropdown in `frontend/index.html`

## Commands

```bash
# Start the server in background (activates venv, runs uvicorn with --reload on port 8001)
# Logs written to server.log
./start.sh

# Stop the background server
./stop.sh

# View server logs
tail -f server.log

# Install dependencies
venv/bin/pip install -r backend/requirements.txt

# Create the Tavus persona (one-time setup, prints persona_id for .env)
venv/bin/python -m scripts.setup_persona

# Upload knowledge base documents (one-time, requires public URLs configured in script)
venv/bin/python -m scripts.upload_documents

# Update persona context with building info + Q&A knowledge base
venv/bin/python -m scripts.update_persona_context

# Syntax-check all backend files
venv/bin/python -m py_compile backend/app.py
```

## Key Files

- **`backend/app.py`** — FastAPI server: 7 API endpoints + serves frontend at `/`. Conversation creation calls Tavus API with persona_id and session properties nested under a `properties` dict.
- **`backend/tavus_client.py`** — Async httpx wrapper for Tavus REST API (`https://tavusapi.com/v2`). All methods are async; auth via `x-api-key` header.
- **`backend/tool_stubs.py`** — Five stubbed tool handlers that log `[STUB]` messages. Each returns a dict with `status` key. Replace these with real integrations for production.
- **`backend/config.py`** — Loads `.env` from project root. Exports: `TAVUS_API_KEY`, `TAVUS_PERSONA_ID`, `TAVUS_REPLICA_ID`, `BACKEND_URL`.
- **`scripts/setup_persona.py`** — Creates the Tavus persona with system prompt, tool definitions, and layer config (Raven-0 perception, Sparrow-1 turn-taking, tavus-gpt-oss LLM, Cartesia TTS).
- **`knowledge-base/building_info.txt`** — Building details (pricing, amenities, policies, contacts) uploaded to Tavus for RAG.
- **`knowledge-base/concierge_qa.txt`** — Q&A interaction examples (visitor ID, delivery, access, leasing, emergencies, escalation) loaded into persona context.
- **`scripts/update_persona_context.py`** — Patches the Tavus persona's `context` field with combined building info and Q&A content.

## Tavus API Conventions

- **Persona creation** (`POST /v2/personas`): Layer field names must match the API schema exactly — e.g., `turn_detection_model` (not `conversational_flow_model`), `turn_taking_patience` (not `patience_level`), `tts_emotion_control` (boolean, not nested object).
- **Conversation creation** (`POST /v2/conversations`): Session settings (`max_call_duration`, `participant_left_timeout`, `enable_closed_captions`, etc.) go inside a `properties` dict, not at the top level.
- **Documents** (`POST /v2/documents`): Require publicly accessible URLs; tagged with `["concierge", "building-info"]` or `["concierge", "faq"]`.

## Patterns

- All Tavus client functions are async. Scripts bridge with `asyncio.run(main())`.
- Request validation uses Pydantic `BaseModel` classes defined in `app.py`.
- Tool stubs are plain synchronous functions (no I/O); called from async endpoints.
- Frontend uses safe DOM methods only (no `innerHTML`) — `textContent` and `createElement`.
- The system prompt encodes behavioral instructions, not hardcoded answers, so the LLM generalizes.
