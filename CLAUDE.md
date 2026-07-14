# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A real-time AI building concierge avatar for "The Meridian" luxury residential building, powered by Tavus.io's Conversational Video Interface (CVI). A FastAPI backend manages conversation lifecycle, tool execution (currently stubbed for demo), admin authentication, and conversation history. Three web portals: visitor portal with Tavus avatar iframe (kiosk mode with face detection auto-start), admin knowledge base editor, and conversation history viewer.

## Architecture

```
Browser (frontend/index.html)
  → POST /api/conversations → FastAPI backend
  → receives conversation_url → loads in iframe (WebRTC to Tavus)
  → Tavus CVI handles STT/LLM/TTS/Avatar rendering
  → LLM tool calls → Tavus webhooks → POST /webhooks/tavus on backend
  → stub handlers log to console, return simulated responses
  → conversation transcript/metadata → SQLite database

Admin Portal (frontend/admin-knowledge-base.html)
  → Cookie-based session auth (2-hour timeout, auto-eviction)
  → Load/edit/save KB files per user
  → Sync KB to Tavus persona context via PATCH API

History Viewer (frontend/conversations.html)
  → Query SQLite conversation logs
  → Filter by date range, sort by newest/oldest/longest
  → Export to JSON or CSV
```

The Tavus persona (created via `scripts/setup_persona.py`) defines the avatar's behavior through a system prompt encoding 9 Q&A categories (visitor ID, access, leasing, directions, packages, amenities, safety, escalation, closing) and 6 tool definitions (notify_resident, unlock_door, schedule_tour, notify_management, log_delivery, escalate_to_human).

**Database Schema:**
- `Conversation` table tracks: conversation_id, started_at, ended_at, duration_seconds, transcript (JSON), visitor_name (extracted from transcript), recording_url, created_at
- SQLite file: `conversations.db` (auto-created on startup)

## Multi-User Support

The application supports multiple users with separate avatars and knowledge bases:

**Users:**
- `admin` - Meridian Building (default)
- `buildingB` - Building B

**Configuration:**
Users are defined in `backend/config.py` USERS dict. Each user has:
- Password (both use "meridian" — stored in plaintext, demo-grade security)
- Tavus persona_id (different avatar personality/behavior)
- Tavus replica_id (different visual appearance)
- KB directory path (separate content: `knowledge-base/{username}/`)

**Login Flow:**
- Visitor portal (`/`): Dropdown selection on login screen, username auto-filled, sessionStorage persists user selection
- Admin portal (`/admin/knowledge-base`): Cookie-based auth via `/admin/auth` endpoint, 2-hour session timeout

**Conversation Flow:**
- Frontend sends `username` in POST /api/conversations
- Backend looks up user config from USERS dict, retrieves persona_id
- Creates conversation with user-specific Tavus persona
- Returns conversation_url for iframe embed

**KB Management:**
- KB editor URL includes user param: `/admin/knowledge-base?user=buildingB`
- Load/save/sync operations target user-specific KB directory
- Sync pushes KB content to Tavus persona via PATCH /personas/{persona_id} API
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
2. Create KB directory: `knowledge-base/<username>/` with `building_info.txt` and `concierge_qa.txt`
3. Add persona/replica env vars to `.env` (e.g., `BUILDINGB_PERSONA_ID`, `BUILDINGB_REPLICA_ID`)
4. Run `setup_persona.py` with new user: `python -m scripts.setup_persona --user <username> --replica <replica_id>`
5. Add option to login dropdown in `frontend/index.html` (line ~150)

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

# Create the Tavus persona for a user (prints persona_id for .env)
# Default user is 'admin'; use --user flag for others
venv/bin/python -m scripts.setup_persona
venv/bin/python -m scripts.setup_persona --user buildingB --replica <replica_id>

# Upload knowledge base documents (one-time, requires public URLs configured in script)
venv/bin/python -m scripts.upload_documents

# Update persona context with building info + Q&A knowledge base
venv/bin/python -m scripts.update_persona_context

# Clean up zombie Tavus conversations (run when hitting concurrent conversation limit)
venv/bin/python scripts/cleanup_conversations.py

# Syntax-check all backend files
venv/bin/python -m py_compile backend/app.py

# Query conversation history (via curl)
curl "http://localhost:8001/api/conversations?days=7&sort=newest"
curl "http://localhost:8001/api/conversations?format=csv" -o conversations.csv
```

## Key Files

- **`backend/app.py`** — FastAPI server with 14 endpoints:
  - Public API: `/api/conversations` (create/end), `/api/conversations` (GET history with filters), tool stub endpoints
  - Admin API: `/admin/auth` (login), `/admin/logout`, `/admin/knowledge-base/*` (load/save/sync KB files)
  - Webhooks: `/webhooks/tavus` (handles conversation_started, tool_called, conversation_ended, recording_available)
  - Pages: `/` (visitor portal), `/conversations` (history viewer), `/admin/knowledge-base` (KB editor)
  - Session management: in-memory dict, 2-hour timeout, auto-eviction at 100 sessions
  - Conversation creation calls Tavus API with persona_id and session properties nested under a `properties` dict
  - Error handling: Returns 503 with `retry_after` field when Tavus concurrent conversation limit is hit; catches `httpx.HTTPStatusError` and inspects response body
- **`backend/models.py`** — SQLAlchemy ORM: `Conversation` table schema, `init_db()`, `get_session()`, `extract_visitor_name()` utility
- **`backend/tavus_client.py`** — Async httpx wrapper for Tavus REST API (`https://tavusapi.com/v2`). All methods are async; auth via `x-api-key` header.
- **`backend/tool_stubs.py`** — Six stubbed tool handlers that log `[STUB]` messages. Each returns a dict with `status` key. Replace these with real integrations for production.
- **`backend/config.py`** — Loads `.env` from project root. Exports: `TAVUS_API_KEY`, `TAVUS_PERSONA_ID`, `TAVUS_REPLICA_ID`, `BACKEND_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `USERS` dict (multi-user config).
- **`scripts/setup_persona.py`** — Creates the Tavus persona with system prompt, tool definitions (6 tools including escalate_to_human), and layer config (Raven-0 perception, Sparrow-1 turn-taking, tavus-gpt-oss LLM, Cartesia TTS). Supports `--user` flag for multi-user personas. Loads KB files and embeds combined context in persona.
- **`knowledge-base/{username}/building_info.txt`** — Building details (pricing, amenities, policies, contacts) per user.
- **`knowledge-base/{username}/concierge_qa.txt`** — Q&A interaction examples per user, loaded into persona context.
- **`scripts/update_persona_context.py`** — Patches the Tavus persona's `context` field with combined building info and Q&A content via PATCH API.
- **`scripts/cleanup_conversations.py`** — Lists and ends all active Tavus conversations. Run when hitting "maximum concurrent conversations" error.
- **`frontend/index.html`** — Visitor portal: user dropdown, login flow, Tavus iframe embed, sessionStorage for user selection. Handles 503 errors with auto-retry. **Critical:** Destroys existing `dailyCall` before creating new Daily.js iframe to prevent "Duplicate DailyIframe instances" error.
- **`frontend/conversations.html`** — Conversation history viewer: date filter (1/7/30/all days), sort (newest/oldest/longest), export (JSON/CSV).
- **`frontend/admin-knowledge-base.html`** — KB editor: user selector, load/edit/save building_info.txt and concierge_qa.txt, sync to Tavus persona.

## Tavus API Conventions

- **Persona creation** (`POST /v2/personas`): Layer field names must match the API schema exactly — e.g., `turn_detection_model` (not `conversational_flow_model`), `turn_taking_patience` (not `patience_level`), `tts_emotion_control` (boolean, not nested object).
- **Conversation creation** (`POST /v2/conversations`): Session settings (`max_call_duration`, `participant_left_timeout`, `enable_closed_captions`, etc.) go inside a `properties` dict, not at the top level.
- **Documents** (`POST /v2/documents`): Require publicly accessible URLs; tagged with `["concierge", "building-info"]` or `["concierge", "faq"]`.

## Deployment

Production server details in `deployment_details.md` and `DEPLOYMENT_STEPS.md`:
- Host: `208.109.191.251`, user: `jnpwladmin`, path: `/home/jnpwladmin/tavus`
- Deploy via `scp` for individual files or tarball method for bulk updates
- On server: `./stop.sh && ./start.sh` to restart uvicorn (runs on port 8001)
- Server runs with `--reload` flag (auto-reloads on file changes)
- Logs: `tail -f server.log` on production server

## Kiosk Mode & Face Detection

**Feature**: Auto-start conversations when face detected, auto-end after person leaves (saves Tavus API costs)

**Architecture**:
- **Background Video**: `meridian_video.mp4` plays muted when idle (no conversation active)
- **Face Detection**: TensorFlow.js + BlazeFace model (GPU-accelerated, 5-10ms inference)
- **Camera**: getUserMedia runs continuously in background for detection (hidden video element)
- **State Machine**: IDLE → STARTING_CONVERSATION → CONVERSATION_ACTIVE → ENDING_CONVERSATION → IDLE
- **Timers**: Face detected for 1.5s → start conversation; No face for 10s → end conversation
- **URL-based login**: `?building=meridian` auto-selects username (no manual login in kiosk)

**Files**:
- `frontend/face-detection.js` — BlazeFace integration, camera access, detection loop
- `frontend/state-machine.js` — State transitions, timer management
- `frontend/index.html` — Kiosk initialization, UI transitions, background video

**Configuration** (`.env`):
```bash
FACE_DETECTION_ENABLED=true
FACE_DETECTION_THRESHOLD=0.75
FACE_START_DELAY=1.5
FACE_END_DELAY=10
MIN_FACE_SIZE=0.15
```

**Deployment** (Chrome kiosk mode):
```bash
chromium-browser --kiosk \
  --use-fake-ui-for-media-stream \
  --autoplay-policy=no-user-gesture-required \
  https://concierge.example.com/?building=meridian
```

## Patterns

- All Tavus client functions are async. Scripts bridge with `asyncio.run(main())`.
- Request validation uses Pydantic `BaseModel` classes defined in `app.py`.
- Tool stubs are plain synchronous functions (no I/O); called from async endpoints.
- Frontend uses safe DOM methods only (no `innerHTML`) — `textContent` and `createElement`.
- The system prompt encodes behavioral instructions, not hardcoded answers, so the LLM generalizes.
- Admin authentication: cookie-based sessions (`admin_session`), validated on protected endpoints via `validate_session()`. No password hashing (demo-grade security).
- Conversation history: SQLite conversation records created via webhook events (`conversation_started`, `conversation_ended`). Transcript extracted from webhook payload and stored as JSON string.
- Multi-user isolation: Each user has separate persona_id, replica_id, and KB directory. Frontend passes `username` to conversation API; backend looks up config from `USERS` dict in `config.py`.
- Kiosk mode: Face detection runs at 5 FPS when idle, 2 FPS during conversation. Multiple faces tracked—conversation only ends when ALL faces gone.
- Error handling: Backend catches `httpx.HTTPStatusError`, inspects `e.response.text` for Tavus-specific errors (e.g., "maximum concurrent conversations"), returns 503 with `retry_after` field. Frontend detects 503, extracts `retry_after`, throws error with `retryAfter` property. State machine detects `error.retryAfter`, schedules delayed retry to IDLE instead of ERROR_RECOVERY.
- Daily.js cleanup: Always call `dailyCall.destroy()` before creating new `Daily.createFrame()` instance to prevent "Duplicate DailyIframe instances" error. Check `if (dailyCall)` before destroy, handle exceptions, set to `null` after.
