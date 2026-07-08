# Build Spec — Presence-Gated Tavus Kiosk Controller

> **How to use this file:** Paste it into Claude Code as the project brief (e.g. save as `SPEC.md` at repo root and tell Claude Code "implement this spec, milestone by milestone"). It is written as an implementation contract: architecture, exact APIs, config, message protocols, thresholds, edge cases, build order, and acceptance criteria.

---

## 1. Goal

Build a kiosk system where an AI video agent (Tavus CVI) attends to walk-up customers, but the **live Tavus conversation only runs while a person is actually present and engaged**. When nobody is there, the screen shows a cheap looping local video and **no Tavus room is open**, so no GPU runtime is billed.

Tavus bills for the wall-clock lifetime of an open conversation regardless of whether anyone is talking, so the entire cost win comes from tightly coupling the conversation lifecycle to confirmed physical presence, plus using Tavus's own timeouts as a backstop.

---

## 2. High-Level Architecture

Two processes on the kiosk/edge box, plus Tavus in the cloud:

```
  Camera ──► Presence Controller (Python) ──► Tavus REST API (create / end conversation)
                     │
                     │  WebSocket (local, localhost)
                     ▼
             Kiosk Frontend (browser, fullscreen)
             ├─ idle:   loops local attract video   (zero Tavus cost)
             ├─ arming: (optional) short greeting bridge clip
             └─ active: embeds Tavus conversation_url (Daily room iframe)
```

- **Presence Controller** — captures the camera, runs local face detection + an engagement gate, runs the lifecycle state machine, calls the Tavus API, and drives the frontend over a local WebSocket.
- **Kiosk Frontend** — a fullscreen browser page. Shows the looping attract video by default; on command, shows a short greeting clip and/or embeds the live Tavus room.
- **Tavus** — creates/ends the conversation; enforces server-side timeouts as a safety net.

### Lifecycle state machine

| State | On screen | Meaning | → transitions |
|-------|-----------|---------|---------------|
| `IDLE` | attract loop | nobody engaged, no Tavus room | engaged face for `arm_debounce_s` → `ARMING` |
| `ARMING` | attract (or greeting) | presence confirmed, spinning up | Tavus create OK → `ACTIVE`; engagement lost → `IDLE`; create fails → `IDLE` (backoff) |
| `ACTIVE` | live Tavus room | conversation running | engagement lost → `GRACE`; room ended (Tavus/Daily) → `IDLE` |
| `GRACE` | live Tavus room | person maybe stepped away | face returns → `ACTIVE`; `grace_s` elapses → **end room** → `IDLE` |

Hysteresis is deliberate: **fast to arm, slow to release**. `ARMING` debounces so passers-by don't trigger a paid session; `GRACE` prevents a brief look-away or occlusion from tearing down and re-billing a session.

---

## 3. Tech Stack & Assumptions

- **Language:** Python 3.11+ for the controller. Plain HTML/JS for the frontend (no build step required for v1).
- **Controller libs:** `opencv-python` (camera), a pluggable detector backend (default `mediapipe`), `httpx` (Tavus API), `websockets` (frontend link), `pydantic`/`PyYAML` (config), `structlog` or stdlib `logging`.
- **Detector backend is pluggable** behind one interface (see §6.1). Ship these:
  - `mediapipe` — **default**. CPU-only, cross-platform, light. Good for mini-PC kiosks.
  - `yolo` — Ultralytics YOLO nano (person/face). For a box with a GPU.
  - `insightface` — highest-quality face + pose. Upgrade path.
  - The hardware target is **not fixed**; the backend is a config value so the same codebase runs on a CPU mini-PC, a GPU edge box, or a Jetson.
- **Frontend runtime:** Chromium in kiosk mode (`--kiosk --autoplay-policy=no-user-gesture-required`). The Tavus `conversation_url` is a Daily room and renders in an `<iframe>`.
- **Process management:** `systemd` units for both processes, `Restart=always`.

---

## 4. Repository Layout

```
tavus-kiosk/
├─ SPEC.md                      # this file
├─ README.md
├─ config.example.yaml
├─ .env.example
├─ controller/
│  ├─ __init__.py
│  ├─ main.py                   # entrypoint: wires everything, runs asyncio loop
│  ├─ config.py                 # pydantic settings loaded from yaml + env
│  ├─ state_machine.py          # the 4-state FSM
│  ├─ detector/
│  │  ├─ base.py                # PresenceDetector interface + PresenceResult
│  │  ├─ mediapipe_backend.py
│  │  ├─ yolo_backend.py
│  │  └─ insightface_backend.py
│  ├─ engagement.py             # bbox-distance + yaw gate, temporal smoothing
│  ├─ tavus_client.py           # create / end / get conversation
│  ├─ frontend_link.py          # websocket server -> frontend commands
│  └─ webhook_server.py         # OPTIONAL: receive Tavus callbacks (see §6.7)
├─ frontend/
│  ├─ index.html
│  ├─ kiosk.js                  # ws client + video/iframe swapping
│  └─ media/
│     ├─ attract.mp4            # placeholder loop now; agent-idle loop later
│     └─ greeting.mp4           # optional short "one moment…" bridge
├─ systemd/
│  ├─ tavus-controller.service
│  └─ tavus-kiosk-browser.service
└─ tests/
   ├─ test_state_machine.py
   ├─ test_engagement.py
   └─ test_tavus_client.py
```

---

## 5. Configuration

`.env` (secrets):

```
TAVUS_API_KEY=sk_...
```

`config.yaml` (behavior):

```yaml
tavus:
  replica_id: "r..."            # required
  persona_id: "p..."            # required
  conversational_context: "You are a friendly receptionist at <place>. Greet the visitor and help them."
  # Server-side backstops (seconds):
  max_call_duration: 600        # hard cap per session
  participant_left_timeout: 20  # Tavus ends the room this long after everyone leaves
  participant_absent_timeout: 60
  callback_url: null            # OPTIONAL public URL; leave null on a NAT'd kiosk

camera:
  device_index: 0
  target_fps: 10                # detection loop fps; 8-10 is plenty
  frame_width: 640
  frame_height: 480

detector:
  backend: "mediapipe"          # mediapipe | yolo | insightface
  min_confidence: 0.6

engagement:
  min_bbox_height_ratio: 0.18   # face height / frame height => "close enough"
  max_yaw_degrees: 25           # |head yaw| below this => "facing the screen"
  arm_debounce_s: 1.5           # engaged this long before ARMING
  grace_s: 12                   # keep room alive this long after engagement lost
  smoothing_window: 5           # frames of temporal smoothing on presence signal

prewarm:
  enabled: false                # v1 off. If true, create the room during ARMING
                                # using a looser approach threshold (see §7).
  approach_bbox_height_ratio: 0.10

frontend:
  ws_host: "127.0.0.1"
  ws_port: 8765
  attract_video: "media/attract.mp4"
  greeting_video: "media/greeting.mp4"
  use_greeting_bridge: true
  greeting_bridge_ms: 3000      # fallback duration if we can't detect room-joined

logging:
  level: "INFO"
  session_metrics: true         # log session start/end + billed duration estimate
```

> **Attract video note (per client requirement):** For now `attract.mp4` is any placeholder loop. Later, replace that single file with a captured idle/greeting clip of the actual Tavus replica so the idle screen and the live agent look identical. This is a **file swap only** — no code change. To capture it later: run one Tavus session and screen-record the replica idling/greeting, trim to a seamless loop, drop it in as `attract.mp4`.

---

## 6. Component Specs

### 6.1 Presence Detector (`detector/base.py`)

Single interface so backends are interchangeable:

```python
@dataclass
class Face:
    bbox: tuple[int, int, int, int]   # x, y, w, h in pixels
    confidence: float
    yaw_degrees: float | None         # +/- from frontal; None if backend can't estimate
    keypoints: dict | None            # eyes/nose/mouth if available

@dataclass
class PresenceResult:
    faces: list[Face]
    frame_height: int

class PresenceDetector(Protocol):
    def detect(self, frame) -> PresenceResult: ...
    def close(self) -> None: ...
```

- **mediapipe backend:** use MediaPipe Face Detection. Estimate a rough yaw from the 6 keypoints (eye/ear symmetry): if only one ear/eye region is confidently placed or the eyes are strongly asymmetric about the nose, the head is turned. Return an approximate `yaw_degrees`.
- **yolo backend:** run a nano face/person model; yaw may be `None` (then the engagement gate falls back to bbox-size + presence only).
- **insightface backend:** returns accurate bbox + pose (yaw/pitch/roll). Best gate quality.

### 6.2 Engagement Gate (`engagement.py`)

Turns raw detections into a boolean `engaged` signal with temporal smoothing.

A face counts as **engaged** this frame if:
1. `bbox.h / frame_height >= min_bbox_height_ratio` (close enough / a distance proxy), **and**
2. `yaw is None` **or** `abs(yaw) <= max_yaw_degrees` (facing the screen).

If multiple faces, use the **largest** (closest) face. Apply a rolling window (`smoothing_window`) — `engaged` flips true/false only when the majority of the window agrees. Emit an `EngagementSignal(engaged: bool, approaching: bool)` each tick, where `approaching` uses the looser `prewarm.approach_bbox_height_ratio` (only consumed if pre-warm is enabled).

### 6.3 State Machine (`state_machine.py`)

Implement the table in §2 as an explicit FSM (enum states, an `on_tick(signal)` method, and side-effect callbacks injected in: `start_conversation()`, `end_conversation()`, `show_attract()`, `show_greeting()`, `show_conversation(url)`).

Timers:
- `ARMING` entered when `engaged` has held for `arm_debounce_s`. (Track the continuous-engaged duration in the gate, not with a sleep.)
- `GRACE` starts a `grace_s` countdown on entry; cancelled if `engaged` returns true (→ back to `ACTIVE`); on expiry → `end_conversation()` → `IDLE`.
- All transitions logged with reason. No blocking sleeps — everything runs in the asyncio tick loop.

### 6.4 Tavus Client (`tavus_client.py`)

**Auth:** header `x-api-key: <TAVUS_API_KEY>`, `Content-Type: application/json`.

**Create conversation** — `POST https://tavusapi.com/v2/conversations`

```json
{
  "replica_id": "<replica_id>",
  "persona_id": "<persona_id>",
  "conversation_name": "kiosk-<iso8601-timestamp>",
  "conversational_context": "<from config>",
  "callback_url": "<config.callback_url, omit if null>",
  "properties": {
    "max_call_duration": 600,
    "participant_left_timeout": 20,
    "participant_absent_timeout": 60,
    "enable_recording": false
  }
}
```

Response contains `conversation_id`, `conversation_url` (the Daily room), and `status`. Hand `conversation_url` to the frontend.

**End conversation** — `POST https://tavusapi.com/v2/conversations/{conversation_id}/end` (header only, no body). Call this immediately when `GRACE` expires — it stops billing at once rather than waiting for the server-side timeout.

**Get conversation (poll)** — `GET https://tavusapi.com/v2/conversations/{conversation_id}` to detect a room that Tavus shut down on its own (hit `max_call_duration`, etc.). Poll every ~15s while `ACTIVE`/`GRACE`; if status is ended, transition to `IDLE`.

Client requirements: async (`httpx.AsyncClient`), timeouts, retry with backoff on 5xx, structured error logging, and **idempotent end** (safe to call end on an already-ended conversation).

### 6.5 Kiosk Frontend (`frontend/`)

`index.html` holds three stacked layers, all absolutely positioned fullscreen:
1. `<video id="attract" loop muted autoplay playsinline>` — the idle loop.
2. `<video id="greeting" muted playsinline>` — hidden until needed.
3. `<iframe id="room" allow="camera; microphone; autoplay">` — hidden until a room URL arrives.

`kiosk.js`:
- Opens a WebSocket to the controller (`ws://127.0.0.1:8765`), auto-reconnects.
- Handles commands (§6.6) by showing exactly one layer and hiding the others.
- On `conversation`, sets the iframe `src` to `conversation_url`.
- **Upgrade path (recommended):** instead of a raw iframe, use the Daily JS SDK to join `conversation_url` so you get real join/leave events and can emit `room_joined` / `room_ended` back to the controller. v1 may use the plain iframe + a fixed greeting-bridge duration.

### 6.6 Controller ↔ Frontend Protocol (WebSocket, JSON)

Controller → Frontend:

```json
{ "cmd": "attract" }
{ "cmd": "greeting" }
{ "cmd": "conversation", "url": "https://tavus.daily.co/..." }
```

Frontend → Controller (optional, when using the Daily SDK):

```json
{ "event": "room_joined" }
{ "event": "room_ended" }
```

If `room_joined` is received, the controller cross-fades from greeting to room immediately (instead of the fixed `greeting_bridge_ms`). If `room_ended` is received, the controller treats the session as over and returns to `IDLE`.

### 6.7 Webhook Server (OPTIONAL — `webhook_server.py`)

Only wire this up if `callback_url` is set to a **publicly reachable** URL (kiosks behind NAT usually can't receive callbacks — skip it and rely on client-side Daily events + the `GET` poll + Tavus's own timeouts).

If enabled, accept `POST` and handle:
- `system.replica_joined` → replica is live; safe to reveal the room.
- `system.shutdown` (has `properties.shutdown_reason`) → room closed server-side; force controller → `IDLE`.
- `application.transcription_ready` → optional: persist transcript for analytics.

---

## 7. Cold-Start Handling

Creating a conversation is **not instant** — the replica takes a few seconds to become ready (Tavus fires `system.replica_joined` for exactly this reason). Two mitigations, both specced:

- **Greeting bridge (default, `use_greeting_bridge: true`):** the instant `ARMING → ACTIVE` fires and the create call is sent, show `greeting.mp4` (a 2–3s local clip of the same avatar saying "Hi there, one moment…"). Reveal the live room when `room_joined` arrives (Daily SDK) or after `greeting_bridge_ms` as a fallback. Near-zero wasted billing.
- **Approach pre-warm (optional, `prewarm.enabled: true`):** create the conversation slightly earlier, while the person is still approaching (looser `approach_bbox_height_ratio`), so the room is ready by the time they arrive. Costs a few seconds of idle billing per session; enable only for high-traffic locations.

---

## 8. Cost & Safety Backstops

Belt-and-suspenders so a crash or network blip can't leave a paid room open:

1. Controller ends the room **explicitly** the moment `GRACE` expires (immediate billing stop).
2. `participant_left_timeout` (small, e.g. 20s) — Tavus kills the room on its own if the client leaves and the explicit end never fires.
3. `max_call_duration` (e.g. 600s) — hard ceiling per session against a stuck room or a loiterer.
4. `GET` status poll every ~15s while active — catches server-side shutdowns and syncs the FSM back to `IDLE`.
5. `systemd Restart=always` on the controller; an orphaned room from a controller crash is still reaped by `participant_left_timeout`.

---

## 9. Observability

- Structured logs on every state transition (from, to, reason, timestamp).
- Per-session metric line on room end: `conversation_id`, start ts, end ts, **estimated billed seconds** (end − create), end reason (grace_expired / max_duration / room_ended / error). This is the number to watch to prove the optimization is working.
- Counters: sessions/hour, false-arm rate (ARMING→IDLE without reaching ACTIVE), average session length.
- A `--debug-overlay` mode that draws the detected face bbox, bbox-height ratio, yaw, engaged/approaching booleans, and current state onto a preview window — essential for tuning thresholds on-site.

---

## 10. Edge Cases To Handle

- **Tavus create fails** (network / 4xx / 5xx): log, return to `IDLE`, exponential backoff before the next attempt so a failing API doesn't hammer.
- **Camera disconnect / read failure:** force `IDLE`, log an alert, keep retrying to reopen the device.
- **Multiple people:** gate on the largest (closest) face; don't spin up multiple rooms.
- **Present but not engaged** (far away, or looking away): not engaged; no session.
- **Rapid enter/exit / dwelling at the threshold distance:** handled by debounce + smoothing + grace hysteresis; verify no flapping.
- **Session hits `max_call_duration` while person still there:** Tavus shuts down; poll/`room_ended` detects it; return to `IDLE` (optionally re-arm immediately if still engaged).
- **Network loss during `ACTIVE`:** detect via poll failure/room error; end + cleanup; return to `IDLE`.
- **Controller crash mid-session:** systemd restarts it into `IDLE`; the orphaned Tavus room is reaped by `participant_left_timeout`.
- **Frontend WS disconnect:** controller keeps running; frontend auto-reconnects and the controller re-sends the current-state command on reconnect.

---

## 11. Build Order (Milestones)

1. **Skeleton & idle screen.** Repo layout, config loading, frontend that loops `attract.mp4`, controller WS server sending `attract`. Verify the loop plays fullscreen and reconnects.
2. **Detection + engagement (dry run).** MediaPipe backend + engagement gate + `--debug-overlay`. Log `engaged`/`approaching` only — no Tavus, no state changes yet. Tune thresholds against the overlay.
3. **State machine (mock Tavus).** Wire the FSM with stubbed `start/end_conversation`. Drive the frontend through attract → greeting → (fake) room → attract purely from presence. Unit-test all transitions.
4. **Real Tavus client.** Implement create/end/get; replace the stubs; run a real gated session end-to-end. Confirm the room opens on approach and **ends within `grace_s` of departure**.
5. **Cold-start polish.** Greeting bridge; optional Daily SDK `room_joined` handshake; optional pre-warm.
6. **Backstops & ops.** Poll loop, session metrics, systemd units, backoff/retry, README with on-site tuning guide.

---

## 12. Acceptance Criteria

- With nobody present, **no Tavus conversation exists** (verify via Tavus dashboard / List Conversations) and the attract loop plays.
- A person approaching and facing the screen for `arm_debounce_s` causes a conversation to be created and become interactive; a greeting bridge (or pre-warm) hides the connect latency.
- When the person leaves, the conversation is **ended within `grace_s + a few seconds`**, confirmed by the logged session end and the Tavus dashboard.
- A brief look-away or momentary occlusion (< `grace_s`) does **not** tear down the session.
- Passers-by who don't stop and face the screen do **not** trigger a paid session (false-arm rate stays low).
- Killing the controller mid-session leaves no indefinitely-open room (reaped by `participant_left_timeout`).
- Swapping `attract.mp4` for a different file changes the idle loop with no code change.
- All FSM transitions and the engagement gate have passing unit tests.

---

## 13. Non-Goals (v1)

- Multi-kiosk orchestration / central dashboard (presence-gating already caps concurrency naturally; revisit later).
- Analytics beyond basic session metrics.
- Speaker/face **recognition** or identity (this is presence + engagement only, no identification).
- Custom LLM/persona authoring (assume the persona already exists in Tavus).
