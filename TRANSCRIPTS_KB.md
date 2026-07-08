# Transcripts, Unanswered Questions & Knowledge-Base Loop

Turns finished conversations into historical records, surfaces the questions the
bot couldn't answer, routes them through expert review + approval, and publishes
approved answers back into the bot's Tavus knowledge base. Multi-tenant: every
record is tagged with which **bot/site** produced it.

## The loop

```
conversation ends
  → Tavus fires application.transcription_ready  (or fallback: GET /ingest-transcript)
  → Python backend (backend/capture.py) stores conversation + transcript in MySQL,
     tagged with this deployment's BOT_ID
  → detects "the bot couldn't answer" turns (deflection phrases) → unanswered_questions
  → [Laravel admin] expert writes an answer → pending_approval
  → [Laravel admin] reviewer approves → published
  → TavusPublisher rebuilds persona context (base + all published Q&A) → PATCH Tavus
```

## Two apps, one MySQL database

| | Python runtime (this repo) | Laravel admin (`admin/`) |
|---|---|---|
| Role | captures data | expert review + approval + publish |
| Writes | bots, conversations, transcript_messages, unanswered_questions | knowledge_answers, status changes, deflection_phrases |
| Reads | deflection_phrases | everything |

MySQL is the integration contract. Schema source of truth = the Laravel
migrations (`admin/database/migrations`); `db/schema.sql` mirrors them for
reference / manual setup.

## Which bot? (multi-tenant identity)

Each deployment is pinned to one bot via env — no login-time selection:

```
# runtime .env for this site
BOT_ID=meridian-01          # must equal a bots.slug in the admin DB
PROPERTY_NAME=The Meridian
DATABASE_URL=mysql+pymysql://user:pass@host:3306/corex?charset=utf8mb4
```

Every conversation/question captured here is tagged with `BOT_ID`, so the admin
can filter "which bot had this problem". If the bot row doesn't exist yet, the
runtime creates it automatically (slug = `BOT_ID`); set its `tavus_persona_id`
and `kb_base_context` in the admin to enable publishing.

## Detecting unanswered questions (no LLM)

Deterministic and admin-tunable: we match the bot's own "I can't help" signals
against each assistant turn and attribute the miss to the **preceding visitor
question**. Signals live in the `deflection_phrases` table (seeded from
`backend/transcripts.py::DEFAULT_DEFLECTION_PHRASES` and the escalation phrases
in `scripts/setup_persona.py`); experts add/disable them per bot in the UI.
Questions are de-duplicated per bot via a normalised hash, so the same question
is never queued twice.

## Runtime pieces (Python)

- **`backend/transcripts.py`** — pure normalise + detect (unit-tested, no DB).
- **`backend/db.py`** — SQLAlchemy tables mirroring the migrations + repository.
- **`backend/capture.py`** — orchestration; best-effort (a DB outage logs a
  warning, never breaks the webhook).
- **`backend/app.py`** — `application.transcription_ready` → ingest; a manual
  `POST /api/conversations/{id}/ingest-transcript` fallback for NAT'd kiosks.
- Config: `BOT_ID`, `PROPERTY_NAME`, `DATABASE_URL`, `CAPTURE_ENABLED`.

> Webhook note: `application.transcription_ready` needs a public `callback_url`.
> On a NAT'd kiosk, poll `POST /api/conversations/{id}/ingest-transcript` (cron
> or the Laravel side) instead.

## Admin (Laravel)

See `admin/README.md`. Drop the files into a fresh Laravel skeleton, point `.env`
at the same MySQL DB, `php artisan migrate --seed`, `php artisan serve`.

## Tests

`venv/Scripts/python -m pytest tests/ -q` — covers transcript normalisation,
detection, dedup, the repository, and end-to-end ingest (SQLite).
