# Plan: Building Concierge Q&A Avatar using Tavus CVI

## Context

The `AI Avatar Interactions.docx` contains a structured Q&A script for a **residential building lobby concierge** — 9 interaction categories, 31 Q&A pairs covering: visitor identification, access/entry, leasing inquiries, navigation, packages, amenities, safety/policies, graceful escalation, and polite closings.

We will implement this as a real-time conversational AI avatar using Tavus.io's CVI, deployed as a **web portal** (browser-based). Backend is **Python/FastAPI**, tool calls are **stubbed/logged** for demo purposes.

---

## Architecture

```
┌──────────────────┐        ┌──────────────────────────────────────┐
│   Web Portal     │  HTTP  │          Tavus CVI Platform          │
│   (Browser)      │◄──────►│                                      │
│                  │ WebRTC │  Phoenix ── STT ── LLM ── TTS       │
│  iframe loading  │        │  Replica   Tavus   tavus   Cartesia  │
│  conversation_url│        │            Adv.    -gpt              │
│                  │        │  Sparrow (flow) + Raven (perception) │
│                  │        │  Knowledge Base (RAG)                │
└────────┬─────────┘        └──────────────┬───────────────────────┘
         │                                 │
         │ POST /api/*                     │ webhooks
         ▼                                 ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                 │
│                                                      │
│  POST /api/conversations   → create Tavus session    │
│  POST /api/notify-resident → stub: log to console    │
│  POST /api/unlock-door     → stub: log to console    │
│  POST /api/schedule-tour   → stub: log to console    │
│  POST /api/notify-mgmt     → stub: log to console    │
│  POST /api/log-delivery    → stub: log to console    │
│  POST /webhooks/tavus      → log transcripts/events  │
└──────────────────────────────────────────────────────┘
```

---

## Step 1: Project Setup

Create the project structure:

```
tavus/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── config.py           # Tavus API key, persona ID, replica ID
│   ├── tavus_client.py     # Tavus API wrapper (persona, conversation, document CRUD)
│   ├── tool_stubs.py       # Stubbed tool call handlers (log to console)
│   └── requirements.txt    # fastapi, uvicorn, httpx, python-dotenv
├── frontend/
│   └── index.html          # Web portal page embedding Tavus CVI via iframe
├── knowledge-base/
│   └── building_info.txt   # Building-specific info for RAG upload
├── scripts/
│   ├── setup_persona.py    # One-time script: create persona via Tavus API
│   └── upload_documents.py # One-time script: upload knowledge base docs
├── .env                    # TAVUS_API_KEY (gitignored)
└── .gitignore
```

**File:** `backend/requirements.txt`
```
fastapi
uvicorn
httpx
python-dotenv
```

---

## Step 2: Create the Concierge Persona

**File:** `scripts/setup_persona.py`

Calls `POST https://tavusapi.com/v2/personas` with this payload:

- **persona_name:** `"Building Concierge"`
- **pipeline_mode:** `"full"`
- **default_replica_id:** `"r1af76e94d00"` (Rose — office/smart casual, warm approachable look)
- **system_prompt:** Encodes all 9 Q&A categories as behavioral instructions (not hardcoded answers):
  - Visitor identification flow (ask name/apt, notify resident)
  - Access rules (never grant without resident confirmation)
  - Leasing info (availability, pricing, tours)
  - Building layout directions (elevators, leasing office, floors)
  - Package/delivery handling
  - Amenity details (gym hours, pool, Wi-Fi)
  - Safety policies (hours, emergencies, overnight rules)
  - Escalation protocol (apologize, offer staff connection)
  - Tone guidance (warm, concise, professional)

- **layers:**
  - `perception`: raven-0, prompt to observe visitor demeanor and packages/uniforms
  - `stt`: tavus-advanced engine, hotwords for apartment numbers and building terms
  - `conversational_flow`: sparrow-1, medium patience, medium interruptibility
  - `llm`: tavus-gpt-oss, temperature 0.6, speculative_inference enabled, 5 tool definitions
  - `tts`: cartesia, emotion_control enabled, positivity:high

### Tool Definitions (5 tools)

| Tool | Trigger | Parameters |
|---|---|---|
| `notify_resident` | Visitor identifies who they're visiting | resident_name, apartment_number, visitor_purpose |
| `unlock_door` | Resident confirms visit (simulated) | door_id, duration_seconds |
| `schedule_tour` | Prospect wants to tour an apartment | visitor_name, contact_info, preferred_date, unit_preferences |
| `notify_management` | Escalation, technical issues, staff requests | reason, urgency |
| `log_delivery` | Delivery person drops off a package | delivery_company, recipient_apartment, package_location |

Script prints the `persona_id` to save in `.env`.

---

## Step 3: Upload Knowledge Base Documents

**File:** `scripts/upload_documents.py`

Calls `POST https://tavusapi.com/v2/documents` to upload:

1. **AI Avatar Interactions.docx** — The full Q&A reference (must be hosted at a public URL first, e.g., S3 or a temp file hosting service). Tagged: `["concierge", "faq"]`

2. **building_info.txt** — Property-specific details:
   - Building name, address, floor count
   - Floor plan pricing
   - Amenity details with hours/locations
   - Leasing office hours
   - Emergency contacts
   - Tagged: `["concierge", "building-info"]`

Script waits for processing confirmation and prints document IDs.

---

## Step 4: FastAPI Backend

**File:** `backend/app.py`

### Endpoints

**`POST /api/conversations`** — Creates a new Tavus conversation:
- Calls `POST https://tavusapi.com/v2/conversations` with:
  - `persona_id` from config
  - `document_tags: ["concierge", "faq", "building-info"]`
  - `callback_url` pointing to `/webhooks/tavus`
  - `enable_closed_captions: true`
  - `max_call_duration: 600` (10 minutes)
  - `participant_left_timeout: 30`
  - `participant_absent_timeout: 120`
- Returns `{ conversation_id, conversation_url }` to frontend

**`POST /api/notify-resident`** — Stub handler:
- Logs: `"[STUB] Notifying resident {name} in apt {number} — purpose: {purpose}"`
- Returns `{ status: "notified", message: "Resident has been notified (simulated)" }`

**`POST /api/unlock-door`** — Stub handler:
- Logs: `"[STUB] Unlocking {door_id} for {duration}s"`
- Returns `{ status: "unlocked", message: "Door unlocked (simulated)" }`

**`POST /api/schedule-tour`** — Stub handler:
- Logs: `"[STUB] Tour scheduled for {name} on {date}"`
- Returns `{ status: "scheduled" }`

**`POST /api/notify-management`** — Stub handler:
- Logs: `"[STUB] Management notified — reason: {reason}, urgency: {urgency}"`
- Returns `{ status: "notified" }`

**`POST /api/log-delivery`** — Stub handler:
- Logs: `"[STUB] Delivery logged — {company} to apt {apartment}, placed in {location}"`
- Returns `{ status: "logged" }`

**`POST /webhooks/tavus`** — Webhook receiver:
- `application.transcription_ready` → Log full transcript
- `application.recording_ready` → Log recording URL
- `system.shutdown` → Log conversation ended
- Returns 200 OK

**File:** `backend/tavus_client.py` — Thin wrapper around Tavus REST API using `httpx`:
- `create_persona(payload)` → POST /v2/personas
- `create_conversation(persona_id, **kwargs)` → POST /v2/conversations
- `upload_document(name, url, tags)` → POST /v2/documents
- `list_conversations()` → GET /v2/conversations
- `end_conversation(id)` → POST /v2/conversations/{id}/end

**File:** `backend/config.py` — Loads from `.env`:
- `TAVUS_API_KEY`
- `TAVUS_PERSONA_ID`
- `TAVUS_REPLICA_ID` (default: `r1af76e94d00`)
- `BACKEND_URL` (for webhook callback)

---

## Step 5: Frontend Web Portal

**File:** `frontend/index.html`

A single-page web portal:
- Header with building name / "Virtual Concierge" title
- "Start Conversation" button that calls `POST /api/conversations`
- Loads the returned `conversation_url` into a centered iframe (camera + mic permissions)
- Shows conversation status (connecting, active, ended)
- "End Conversation" button to close the session
- Minimal, clean CSS — professional lobby aesthetic

The iframe approach is sufficient for the web portal since tool calls are handled server-side via webhooks (Tavus broadcasts tool call events to the callback URL). No client-side Daily SDK or React needed for the stub/demo phase.

---

## Step 6: Conversation Flow Mapping

How each Q&A category from the document maps to the implementation:

| # | Q&A Category | Handled By | Tool Calls |
|---|---|---|---|
| 1 | Visitor Identification & Purpose | System prompt instructs LLM to ask name/apt | `notify_resident` |
| 2 | Access & Entry | System prompt rules (never grant without confirmation) | `unlock_door`, `notify_management` |
| 3 | Leasing & Availability | Knowledge base RAG (building_info.txt pricing) | `schedule_tour` |
| 4 | Directions & Navigation | System prompt (building layout section) | — |
| 5 | Packages & Deliveries | System prompt + LLM | `log_delivery`, `notify_resident` |
| 6 | Amenities & Features | Knowledge base + system prompt | — |
| 7 | Safety, Rules & Policies | Knowledge base + system prompt | `notify_management` |
| 8 | Graceful Escalation | System prompt (escalation rules) | `notify_management` |
| 9 | Polite Closing | System prompt (tone section) | — |

---

## Step 7: Verification

### Setup Verification
1. Run `python scripts/setup_persona.py` — confirm `persona_id` returned
2. Run `python scripts/upload_documents.py` — confirm document IDs, wait for processing
3. Start backend: `uvicorn backend.app:app --reload --port 8001`
4. Open `frontend/index.html` in browser (or serve via FastAPI static files)

### Functional Testing (walk through all 9 categories)
1. Click "Start Conversation" — verify avatar appears and greets
2. Say: "Hi, I'm here to see John Smith in apartment 412" → avatar asks to confirm, backend logs `notify_resident` tool call
3. Say: "How do I get inside?" → avatar explains access process
4. Say: "Are there any apartments available?" → avatar references pricing from knowledge base
5. Say: "Where is apartment 412?" → avatar gives floor + elevator directions
6. Say: "I'm dropping off a package" → avatar directs to package room, backend logs `log_delivery`
7. Say: "Do you have a gym?" → avatar references fitness center (2nd floor, 6AM-10PM)
8. Say: "What if there's an emergency?" → avatar says call 911
9. Say: "This isn't working" → avatar apologizes, backend logs `notify_management`
10. Say: "Thanks, that's all" → avatar closes warmly
11. Check backend console for all stubbed tool call logs and webhook events

### Edge Cases to Test
- Silence / timeout behavior (participant_absent_timeout)
- User walks away mid-conversation (participant_left_timeout)
- Rapid questions in sequence
- Interrupting the avatar mid-sentence
- Questions not in the Q&A doc (should still respond reasonably)

---

## Files to Create/Modify

| File | Action |
|---|---|
| `backend/app.py` | Create — FastAPI server |
| `backend/config.py` | Create — Environment config |
| `backend/tavus_client.py` | Create — Tavus API wrapper |
| `backend/tool_stubs.py` | Create — Stubbed tool handlers |
| `backend/requirements.txt` | Create — Python dependencies |
| `frontend/index.html` | Create — Web portal page |
| `knowledge-base/building_info.txt` | Create — Building info for RAG |
| `scripts/setup_persona.py` | Create — Persona creation script |
| `scripts/upload_documents.py` | Create — Document upload script |
| `.env` | Create — API key (gitignored) |
| `.gitignore` | Create — Ignore .env, __pycache__ |
