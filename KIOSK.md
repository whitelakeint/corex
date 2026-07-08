# Presence-Gated Tavus Kiosk

Couples the Tavus conversation lifecycle to **confirmed physical presence**. When
nobody is engaged, the screen loops a cheap local `attract.mp4` and **no Tavus
room is open** (zero GPU billing). When a person approaches and faces the screen,
the controller opens a Tavus room, shows a short greeting bridge to mask
cold-start, and reveals the live agent. When they leave, the room is ended within
`grace_s`.

Implements `presence-gated-tavus-kiosk-spec.md`, integrated into this repo (reuses
the existing FastAPI backend, Tavus client, and Daily/Jitsi frontend).

## Architecture

```
Camera ─► controller (Python) ─► Tavus REST API (create / end / poll)
             │
             │  local WebSocket (127.0.0.1:8765)
             ▼
      Browser portal (frontend/index.html + kiosk.js), served by the backend
      ├─ idle:   loops attract.mp4              (no Tavus cost)
      ├─ arming: greeting bridge clip
      └─ active: live Tavus room (Daily) — reuses the existing concierge UI
```

- **`controller/`** — camera capture, pluggable face detector, engagement gate,
  the 4-state FSM (`IDLE→ARMING→ACTIVE→GRACE`), Tavus client (retry + idempotent
  end), and the WebSocket that drives the browser.
- **`frontend/`** — the existing portal, adapted: `kiosk.js` reads `/api/config`,
  and in kiosk mode hides the login screen, shows the attract/greeting video
  layers, and joins the Tavus room on the controller's command.
- **`backend/`** — unchanged concierge API + a new `/api/config` endpoint that
  tells the page whether to run as a manual portal or a presence-gated kiosk.

## Running it

1. **Install deps** (into the project venv):
   ```
   venv/Scripts/pip install -r backend/requirements.txt
   venv/Scripts/pip install -r controller/requirements.txt
   ```
   You only need the detector backend you actually run (see below).

2. **Configure**: copy the examples and fill them in.
   ```
   cp .env.example .env                 # TAVUS_API_KEY, TAVUS_PERSONA_ID, KIOSK_MODE=true
   cp config.example.yaml config.yaml   # detector, thresholds, timeouts
   ```
   Set `KIOSK_MODE=true` in `.env` so the browser skips login and runs
   presence-driven. The **property is fixed by config/env** (`PROPERTY_NAME` or
   `property.name` in `config.yaml`) — there is no login-time property selection.

3. **Start the backend** (serves the portal at `/`):
   ```
   ./start.sh          # or: venv/Scripts/uvicorn backend.app:app --port 8001
   ```

4. **Start the controller**:
   ```
   venv/Scripts/python -m controller.main
   # tuning window with bbox/yaw/state overlays:
   venv/Scripts/python -m controller.main --debug-overlay
   ```

5. **Open the kiosk browser** fullscreen at `http://localhost:8001/`
   (Chromium: `--kiosk --autoplay-policy=no-user-gesture-required`).

The idle loop plays. Walk up and face the camera for `arm_debounce_s` → a room
opens. Walk away → it ends within ~`grace_s`.

### Modes (via `.env`)
| `KIOSK_MODE` | `SKIP_LOGIN` | Behaviour |
|---|---|---|
| `false` | `false` | Original manual portal: login → Start button. |
| `false` | `true`  | No login gate; property from env; still manual Start. |
| `true`  | —       | Full presence-gated kiosk (implies skip login). |

## Detector backends (`detector.backend` in config.yaml)

| Backend | Deps | Yaw (facing) | Notes |
|---|---|---|---|
| `opencv` *(default)* | opencv-python only | approx (profile cascade) | Zero-friction; runs anywhere. |
| `mediapipe` | mediapipe | approx (eye/nose asymmetry) | Spec default; light, CPU. |
| `yolo` | ultralytics | none (distance-only gate) | For a GPU box; person detection. |
| `insightface` | insightface + onnxruntime | accurate (real pose) | Best gate quality; GPU upgrade path. |

> Use stable OpenCV **4.x** (`opencv-python>=4.8,<5`). The 5.0 alpha wheels drop
> the Haar `CascadeClassifier` the `opencv` backend needs.

## On-site tuning

Run with `--debug-overlay` and watch the HUD (bbox ratio, yaw, engaged/held,
state, grace countdown). Then adjust `config.yaml → engagement`:

- **Arms too eagerly for passers-by** → raise `min_bbox_height_ratio` (must be
  closer) and/or increase `arm_debounce_s`.
- **Doesn't arm when someone is clearly there** → lower `min_bbox_height_ratio`,
  or loosen `max_yaw_degrees`, or (yolo) accept yaw-less gating.
- **Tears down on a brief look-away** → raise `grace_s`.
- **Flicker at the threshold distance** → raise `smoothing_window`.

## Cost & safety backstops

1. Controller ends the room the instant `GRACE` expires (immediate billing stop).
2. `participant_left_timeout` (Tavus-side) reaps a room if the client leaves and
   the explicit end never fires.
3. `max_call_duration` — hard per-session ceiling.
4. `GET` status poll every ~15s while active — syncs the FSM if Tavus shut a room
   down on its own.
5. `systemd Restart=always`; an orphaned room from a crash is reaped by (2).

## Observability

- Every FSM transition logs `from → to (reason)`.
- On room end: `SESSION_END conversation_id=… start=… billed_seconds=… reason=…`
  plus running `sessions` / `false_arms` counters — the numbers that prove the
  optimization works.

## Tests

```
venv/Scripts/python -m pytest tests/ -q
```
Covers the FSM transitions, the engagement gate (distance/yaw/smoothing/dwell),
and the Tavus client (create body, retry/backoff, idempotent end).
