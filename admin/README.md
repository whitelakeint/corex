# Core X — Knowledge Admin (Laravel)

The staff-facing admin for the concierge bots. It reads the transcripts and
"unanswered questions" that the Python runtime captures into MySQL, lets experts
answer them, routes answers through approval, and on approval **publishes** the
answer into that bot's Tavus knowledge base.

This folder holds the **app-specific files only** — drop them into a fresh
Laravel skeleton (they're the parts you'd otherwise write by hand).

## Setup

```bash
# 1. Create a Laravel app (PHP 8.2+, Composer)
composer create-project laravel/laravel corex-admin
cd corex-admin

# 2. Copy these files in (overwriting where they overlap)
#    app/  config/  database/  resources/  routes/   from this admin/ folder

# 3. Configure .env (see admin/.env.example) — point DB_* at the SAME MySQL
#    database the Python runtime uses, and set TAVUS_* for publishing.

# 4. Create the database + tables
mysql -u root -e "CREATE DATABASE IF NOT EXISTS corex CHARACTER SET utf8mb4"
php artisan migrate --seed        # seeds one example bot + global deflection phrases

# 5. Run it
php artisan serve                 # http://localhost:8000
```

> On XAMPP you can also just point a vhost at the app's `public/` folder.

## How it connects to the runtime

- The **Python backend/controller** writes `bots`, `conversations`,
  `transcript_messages`, and `unanswered_questions` (see `backend/capture.py`).
- Each deployment's `BOT_ID` (runtime `.env`) must equal a `bots.slug` here so
  captured data lines up with the right bot. The seeder creates `meridian-01`;
  set `BOT_ID=meridian-01` in that site's runtime `.env`.
- Detection uses the `deflection_phrases` table — edit/disable rows to tune what
  counts as "the bot couldn't answer" (the runtime reads active rows live).

## Workflow

1. **Unanswered Questions** — queue of questions the bot deflected, filterable by
   bot. Open one to see the full conversation transcript.
2. **Answer** — an expert writes the correct answer → status `pending_approval`.
3. **Approvals** — a reviewer approves (→ published) or rejects (→ back to queue).
4. **Publish** — on approval, `TavusPublisher` rebuilds the bot's persona context
   (`kb_base_context` + all published Q&A) and `PATCH`es it to Tavus. Rebuilding
   is idempotent, so re-publishing never duplicates entries.

## Files in this scaffold

```
app/Http/Controllers/  Dashboard, UnansweredQuestion, KnowledgeAnswer, Approval
app/Models/            Bot, Conversation, TranscriptMessage, DeflectionPhrase,
                       UnansweredQuestion, KnowledgeAnswer
app/Services/          TavusPublisher (rebuild + PATCH persona context)
config/tavus.php       Tavus credentials/config
database/migrations/   the 6 tables (schema source of truth)
database/seeders/      BotSeeder, DeflectionPhraseSeeder
resources/views/       dashboard, questions (index/show), approvals
routes/web.php         routes
```
