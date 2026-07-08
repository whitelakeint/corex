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

## Presence-Gated Kiosk (controller/)

An optional second process turns the portal into a **presence-gated kiosk**: the
Tavus room is only open while a person is actually engaged, so no GPU time is
billed to an empty lobby. See `KIOSK.md` for the full guide. Toggle it with
`KIOSK_MODE=true` in `.env` (the browser then skips login and runs presence-driven
via a local WebSocket). Spec: `presence-gated-tavus-kiosk-spec.md`.

- **`controller/main.py`** — asyncio entrypoint: camera loop → detector →
  engagement gate → FSM; bridges the sync FSM's callbacks to async Tavus/WS work.
  `--debug-overlay` draws bbox/yaw/state for on-site tuning.
- **`controller/state_machine.py`** — pure, synchronous `IDLE→ARMING→ACTIVE→GRACE`
  FSM. Async create is reported back via `notify_conversation_started/_failed`;
  external shutdowns via `notify_room_ended`. Fully unit-tested.
- **`controller/detector/`** — pluggable `PresenceDetector` interface + four
  backends: `opencv` (default, Haar, zero extra deps), `mediapipe`, `yolo`,
  `insightface`. Selected by `detector.backend` in `config.yaml`.
- **`controller/engagement.py`** — distance (bbox ratio) + yaw gate with rolling
  majority smoothing and a monotonic dwell timer (for `arm_debounce_s`).
- **`controller/tavus_client.py`** — wraps `backend.tavus_client` with retry/
  backoff and an idempotent, never-raising `end` (billing safety).
- **`controller/frontend_link.py`** — local WebSocket; broadcasts `attract`/
  `greeting`/`conversation` commands, caches the last one to resync reconnects,
  and forwards `room_joined`/`room_ended` events back.
- **`controller/config.py`** — pydantic config from `config.yaml` (+ env for the
  `TAVUS_API_KEY` secret and `PROPERTY_NAME`). NOTE: the `property` field shadows
  the builtin, so `ws_url` is a method, not a `@property`.
- **`frontend/kiosk.js`** — reads `/api/config`; in kiosk mode drives the video
  layers and calls `window.ConciergeApp.openRoom/closeRoom` (defined in
  `index.html`) to reuse the existing Daily join + Jitsi escalation.
- Config comes from `config.yaml` (copy from `config.example.yaml`); the property
  is fixed by config/env rather than chosen at a login screen.

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

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |
