# Kiosk media

Drop two video files here (they are intentionally **not** committed — they're
large binaries and site-specific):

| File           | Role                                                            |
|----------------|-----------------------------------------------------------------|
| `attract.mp4`  | Looping idle screen shown while nobody is engaged. **Zero Tavus cost.** |
| `greeting.mp4` | Short (2–3s) "Hi there, one moment…" bridge clip while the room spins up. |

If a file is missing the kiosk shows a styled CSS fallback (brand mark +
"Step closer to begin"), so the kiosk still works before you produce the clips.

## Producing them later (file swap only — no code change)

Per the client requirement, replace `attract.mp4` with a captured idle/greeting
clip of the **actual Tavus replica** so the idle screen and the live agent look
identical:

1. Run one real Tavus session and screen-record the replica idling/greeting.
2. Trim to a seamless loop (attract) and a short greeting (greeting).
3. Drop them in here as `attract.mp4` / `greeting.mp4`.

Paths are configured in `config.yaml` under `frontend.attract_video` /
`frontend.greeting_video` and referenced by `frontend/index.html`.
