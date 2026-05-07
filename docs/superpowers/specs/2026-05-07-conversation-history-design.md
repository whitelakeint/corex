# Conversation History Storage and Display Design

**Date:** 2026-05-07  
**Project:** The Meridian AI Concierge  
**Status:** Approved for Implementation

---

## Context

The Meridian AI concierge currently handles visitor conversations through Tavus CVI but has no persistent storage. All conversation data—transcripts, visitor information, and interaction metadata—is lost after webhook processing. This makes it impossible to:

- Review past visitor interactions
- Identify patterns or recurring issues
- Audit concierge performance
- Retrieve conversation history for follow-up

This design adds persistent conversation storage and a web-based history viewer with time-range filtering, sorting, transcript viewing, and CSV export capabilities.

---

## Requirements

**Must Have:**
- Store basic conversation metadata (conversation_id, timestamps, duration)
- Store full transcript in text format
- Optionally capture visitor name (if mentioned in conversation)
- Web page at `/conversations` showing conversation list
- Time-based filters: 1 day, 2 days, 7 days, 30 days, All
- Sort options: Newest First, Oldest First, Longest Duration
- Click to expand and view full transcript
- Export filtered results as CSV
- Public access (no authentication required)

**Out of Scope:**
- Real-time conversation streaming
- Tool usage analytics
- Escalation tracking
- User authentication/authorization
- Search by visitor name or content
- Advanced analytics or reporting

---

## Architecture Overview

### Components

1. **Database Layer** (SQLite + SQLAlchemy ORM)
   - Single database file: `conversations.db` in project root
   - One table: `conversations`
   - SQLAlchemy models in new file `backend/models.py`
   - Database initialization on FastAPI app startup

2. **Data Capture** (Webhook Enhancement)
   - Extend existing `/webhooks/tavus` endpoint
   - Detect `application.transcription_ready` event
   - Extract conversation metadata and full transcript
   - Parse visitor name via regex patterns (optional)
   - Insert record into database

3. **History API** (New FastAPI Endpoint)
   - GET `/api/conversations` with query params for filtering/sorting
   - Returns JSON or CSV format
   - SQLAlchemy queries with time-range and sort logic

4. **Frontend Page** (New HTML)
   - Route: `/conversations` served by FastAPI
   - Table view with expandable transcript rows
   - Filter/sort controls
   - CSV export button
   - Responsive design matching existing frontend

### Data Flow

```
Tavus Conversation Ends
  → Tavus sends transcription_ready webhook
  → Backend parses payload
  → Extract metadata + transcript
  → Optional: Extract visitor name via regex
  → Insert into SQLite database
  → User visits /conversations page
  → Frontend fetches /api/conversations
  → Displays table with filters
  → User clicks "View Transcript" or "Export CSV"
```

---

## Data Model

### SQLite Schema - `conversations` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `conversation_id` | TEXT | UNIQUE NOT NULL | Tavus conversation UUID |
| `started_at` | DATETIME | | Conversation start timestamp |
| `ended_at` | DATETIME | | Conversation end timestamp |
| `duration_seconds` | INTEGER | | Calculated duration in seconds |
| `transcript` | TEXT | | Full transcript as JSON string |
| `visitor_name` | TEXT | NULLABLE | Extracted visitor name (optional) |
| `recording_url` | TEXT | NULLABLE | Tavus recording URL if available |
| `created_at` | DATETIME | DEFAULT NOW | Database insert timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `conversation_id` (prevents duplicate inserts)
- Index on `created_at` (optimizes time-range queries)

### Transcript Format

Stored as JSON string containing array of conversation exchanges:

```json
[
  {"speaker": "avatar", "text": "Welcome to The Meridian. How can I help you?"},
  {"speaker": "visitor", "text": "I'm here to see John Smith in unit 405."},
  {"speaker": "avatar", "text": "Let me notify the resident for you."}
]
```

### Visitor Name Extraction

**Why:** Visitor identification is optional but valuable for context. The system attempts to extract names mentioned during conversation.

**How to apply:** Use regex patterns to search concatenated transcript text:
- Pattern: `"I'm here to see ([A-Z][a-z]+ [A-Z][a-z]+)"`
- Pattern: `"[Mm]y name is ([A-Z][a-z]+ [A-Z][a-z]+)"`
- Pattern: `"[Tt]his is ([A-Z][a-z]+ [A-Z][a-z]+)"`
- Pattern: `"I am ([A-Z][a-z]+ [A-Z][a-z]+)"`

Store first match or NULL if none found.

### SQLAlchemy Model

**File:** `backend/models.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), unique=True, nullable=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    transcript = Column(Text)
    visitor_name = Column(String(255), nullable=True)
    recording_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database initialization
def init_db(database_url="sqlite:///conversations.db"):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
```

---

## Webhook Enhancement

### Current Behavior

The existing `/webhooks/tavus` endpoint in `backend/app.py`:
- Receives POST with `event_type` and payload
- Dispatches tool calls to stubs
- Returns 200 OK

### New Behavior

**Why:** Tavus sends `application.transcription_ready` after conversation ends with full transcript. This is the trigger for persistent storage.

**How to apply:** Add detection and storage logic:

1. Check if `event_type == "application.transcription_ready"`
2. Extract required fields from webhook payload
3. Calculate conversation duration
4. Convert transcript array to JSON string
5. Run visitor name extraction on transcript text
6. Create SQLAlchemy `Conversation` object
7. Insert into database (handle duplicates gracefully)
8. Log success or errors

### Expected Webhook Payload

```json
{
  "event_type": "application.transcription_ready",
  "conversation_id": "conv_abc123",
  "properties": {
    "transcript": [
      {"role": "assistant", "content": "Welcome to The Meridian"},
      {"role": "user", "content": "I'm here to see John Smith"}
    ],
    "started_at": "2026-05-07T10:30:00Z",
    "ended_at": "2026-05-07T10:35:00Z",
    "recording_url": "https://tavus.io/recordings/abc123"
  }
}
```

### Implementation Logic

```python
import re
import json
from datetime import datetime

def extract_visitor_name(transcript_text: str) -> str | None:
    """Extract visitor name from transcript using regex patterns."""
    patterns = [
        r"I'm here to see ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"[Mm]y name is ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"[Tt]his is ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"I am ([A-Z][a-z]+ [A-Z][a-z]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, transcript_text)
        if match:
            return match.group(1)
    return None

# In webhook handler:
if event_type == "application.transcription_ready":
    try:
        conversation_id = payload["conversation_id"]
        props = payload.get("properties", {})
        
        # Parse timestamps
        started_at = datetime.fromisoformat(props["started_at"].replace("Z", "+00:00"))
        ended_at = datetime.fromisoformat(props["ended_at"].replace("Z", "+00:00"))
        duration_seconds = int((ended_at - started_at).total_seconds())
        
        # Process transcript
        transcript_array = props["transcript"]
        transcript_json = json.dumps(transcript_array)
        
        # Extract visitor name
        transcript_text = " ".join([msg["content"] for msg in transcript_array])
        visitor_name = extract_visitor_name(transcript_text)
        
        # Get recording URL if available
        recording_url = props.get("recording_url")
        
        # Insert into database
        conversation = Conversation(
            conversation_id=conversation_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            transcript=transcript_json,
            visitor_name=visitor_name,
            recording_url=recording_url
        )
        
        db_session.add(conversation)
        db_session.commit()
        logger.info(f"Stored conversation: {conversation_id}")
        
    except IntegrityError:
        # Duplicate conversation_id - already stored
        db_session.rollback()
        logger.info(f"Conversation {conversation_id} already exists")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to store conversation: {e}")
```

### Error Handling

- **Database connection failure:** Log error, return 500
- **Missing required fields:** Log warning, return 200 (acknowledge webhook)
- **Duplicate conversation_id:** Log info, rollback, return 200 (idempotent)
- **Invalid timestamp format:** Log error, skip record, return 200
- **JSON serialization error:** Log error, skip record, return 200

---

## History API Endpoint

### Endpoint: GET `/api/conversations`

**Why:** Frontend needs a queryable API to fetch conversation history with flexible filtering and sorting. Supporting both JSON and CSV formats enables programmatic access and manual exports.

**How to apply:**

**Query Parameters:**
- `days` (optional, default: `"7"`) — Time range filter: `"1"`, `"2"`, `"7"`, `"30"`, `"all"`
- `sort` (optional, default: `"newest"`) — Sort order: `"newest"`, `"oldest"`, `"longest"`
- `format` (optional, default: `"json"`) — Response format: `"json"`, `"csv"`

**Response Format - JSON:**

```json
{
  "conversations": [
    {
      "id": 1,
      "conversation_id": "conv_abc123",
      "started_at": "2026-05-07T10:30:00Z",
      "ended_at": "2026-05-07T10:35:00Z",
      "duration_seconds": 300,
      "visitor_name": "John Smith",
      "recording_url": "https://tavus.io/recordings/abc123",
      "transcript": [
        {"speaker": "avatar", "text": "Welcome to The Meridian"},
        {"speaker": "visitor", "text": "I'm here to see John Smith"}
      ]
    }
  ],
  "total": 42,
  "filters": {"days": "7", "sort": "newest"}
}
```

**Response Format - CSV:**

```csv
ID,Conversation ID,Started At,Ended At,Duration (seconds),Visitor Name,Recording URL,Transcript
1,conv_abc123,2026-05-07 10:30:00,2026-05-07 10:35:00,300,John Smith,https://tavus.io/recordings/abc123,"Avatar: Welcome... Visitor: I'm here..."
```

### Implementation Logic

**Time Filtering:**
- Calculate cutoff timestamp: `datetime.utcnow() - timedelta(days=int(days))`
- SQLAlchemy query: `WHERE created_at >= cutoff_timestamp`
- If `days == "all"`, skip time filter

**Sorting:**
- `"newest"`: `ORDER BY created_at DESC`
- `"oldest"`: `ORDER BY created_at ASC`
- `"longest"`: `ORDER BY duration_seconds DESC, created_at DESC`

**Transcript Processing:**
- For JSON: Parse stored JSON string back to array
- For CSV: Flatten to single text block with speaker prefixes

**CSV Generation:**
- Use Python `csv` module
- Set response headers:
  - `Content-Type: text/csv`
  - `Content-Disposition: attachment; filename="conversations-{timestamp}.csv"`
- Escape quotes, newlines, commas in transcript column

**SQLAlchemy Query Example:**

```python
from datetime import datetime, timedelta
from sqlalchemy import desc, asc

def query_conversations(db_session, days="7", sort="newest"):
    query = db_session.query(Conversation)
    
    # Time filter
    if days != "all":
        cutoff = datetime.utcnow() - timedelta(days=int(days))
        query = query.filter(Conversation.created_at >= cutoff)
    
    # Sort
    if sort == "newest":
        query = query.order_by(desc(Conversation.created_at))
    elif sort == "oldest":
        query = query.order_by(asc(Conversation.created_at))
    elif sort == "longest":
        query = query.order_by(
            desc(Conversation.duration_seconds),
            desc(Conversation.created_at)
        )
    
    return query.all()
```

---

## Frontend Page

### Route: `/conversations`

**Why:** Users need a visual interface to browse conversation history without command-line tools or database access. Time-based filtering and sorting enable quick access to recent or long conversations.

**How to apply:**

### HTML Structure

**File:** `frontend/conversations.html`

**Layout:**

1. **Header Section:**
   - Page title: "Conversation History - The Meridian"
   - Filter button group: [1 Day] [2 Days] [7 Days] [30 Days] [All]
   - Sort dropdown: "Newest First" | "Oldest First" | "Longest Duration"
   - Export CSV button (styled prominently)
   - Results count: "Showing 42 conversations"

2. **Conversations Table:**

| Date & Time | Duration | Visitor | Actions |
|-------------|----------|---------|---------|
| May 7, 10:30 AM | 5m 0s | John Smith | [View Transcript] [Recording] |
| May 7, 9:15 AM | 3m 45s | (Unknown) | [View Transcript] |
| May 6, 4:20 PM | 12m 30s | Sarah Johnson | [View Transcript] [Recording] |

3. **Expanded Transcript Row:**
   - Shows after clicking "View Transcript"
   - Formatted conversation with speaker labels
   - Avatar messages styled differently from visitor messages
   - Scrollable if transcript is long
   - [Collapse] button to close

4. **Empty State:**
   - Message: "No conversations found for this time period"
   - Suggestion: "Try selecting a different time range"

### Styling

- Match existing frontend theme from `index.html` (dark background, modern aesthetic)
- Responsive table layout (mobile-friendly)
- Active filter button highlighted with accent color
- Loading spinner while fetching data
- Hover effects on table rows
- Smooth expand/collapse animation

### JavaScript Behavior

**On Page Load:**
```javascript
// Default: 7 days, newest first
fetchConversations(days=7, sort='newest');
setActiveFilter('7-days');
```

**Filter Button Click:**
```javascript
filterButton.addEventListener('click', (e) => {
  const days = e.target.dataset.days;
  setActiveFilter(e.target.id);
  fetchConversations(days, currentSort);
});
```

**Sort Dropdown Change:**
```javascript
sortDropdown.addEventListener('change', (e) => {
  const sort = e.target.value;
  currentSort = sort;
  fetchConversations(currentDays, sort);
});
```

**View Transcript Click:**
```javascript
viewButton.addEventListener('click', (e) => {
  const row = e.target.closest('tr');
  const transcriptRow = row.nextElementSibling;
  
  if (transcriptRow.classList.contains('expanded')) {
    transcriptRow.classList.remove('expanded');
  } else {
    const transcript = JSON.parse(row.dataset.transcript);
    renderTranscript(transcriptRow, transcript);
    transcriptRow.classList.add('expanded');
  }
});
```

**Export CSV Click:**
```javascript
exportButton.addEventListener('click', () => {
  const url = `/api/conversations?days=${currentDays}&sort=${currentSort}&format=csv`;
  window.location.href = url; // Triggers download
});
```

**Recording Link:**
```javascript
// Open in new tab if URL exists
if (recording_url) {
  recordingLink.href = recording_url;
  recordingLink.target = '_blank';
} else {
  recordingLink.classList.add('disabled');
  recordingLink.removeAttribute('href');
}
```

### Safe DOM Manipulation

**Why:** User-provided data (visitor names, transcript content) must be safely rendered to prevent XSS attacks.

**How to apply:**
- ALWAYS use `createElement` and `textContent` (NEVER use the unsafe property that starts with "inner" and ends with "HTML")
- Escape user data before rendering
- If rich formatting is needed later, use DOMPurify library

```javascript
function renderTranscript(container, transcript) {
  // Clear previous content safely
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }
  
  transcript.forEach(exchange => {
    const div = document.createElement('div');
    div.className = exchange.speaker === 'avatar' ? 'message-avatar' : 'message-visitor';
    
    const label = document.createElement('strong');
    label.textContent = exchange.speaker === 'avatar' ? 'Avatar: ' : 'Visitor: ';
    
    const text = document.createElement('span');
    text.textContent = exchange.text; // Safe - uses textContent
    
    div.appendChild(label);
    div.appendChild(text);
    container.appendChild(div);
  });
}
```

### Error Handling

- **Network error:** Show toast notification "Failed to load conversations. Please try again."
- **Empty results:** Display friendly empty state with suggestions
- **Invalid parameters:** Log error, fall back to defaults (7 days, newest)
- **Parse error:** Log error, skip malformed record, continue rendering others

---

## Dependencies

### New Python Packages

Add to `backend/requirements.txt`:

```
sqlalchemy
```

SQLite driver is built into Python, no additional package needed.

### Installation

```bash
venv/bin/pip install sqlalchemy
```

---

## Database Initialization

**Why:** Database must be created and schema initialized before the app can store conversations.

**How to apply:**

1. Add database initialization to FastAPI startup event
2. Create `conversations.db` file in project root
3. Run SQLAlchemy `create_all()` to create tables

**Code in `backend/app.py`:**

```python
from backend.models import init_db, get_session

# Global database session
db_engine = None
db_session = None

@app.on_event("startup")
async def startup_event():
    global db_engine, db_session
    db_engine = init_db("sqlite:///conversations.db")
    db_session = get_session(db_engine)
    logger.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    if db_session:
        db_session.close()
    logger.info("Database connection closed")
```

---

## Verification Plan

### 1. Database Setup

**Verify database file created:**
```bash
ls -lh conversations.db
```

**Verify schema:**
```bash
venv/bin/python -c "
from backend.models import Base, Conversation
from sqlalchemy import create_engine, inspect

engine = create_engine('sqlite:///conversations.db')
inspector = inspect(engine)

print('Tables:', inspector.get_table_names())
print('Columns:', inspector.get_columns('conversations'))
print('Indexes:', inspector.get_indexes('conversations'))
"
```

### 2. Webhook Testing

**Simulate transcription_ready webhook:**
```bash
curl -X POST http://localhost:8001/webhooks/tavus \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "application.transcription_ready",
    "conversation_id": "test_conv_001",
    "properties": {
      "transcript": [
        {"role": "assistant", "content": "Welcome to The Meridian. How can I help you?"},
        {"role": "user", "content": "I am here to see John Smith in unit 405."}
      ],
      "started_at": "2026-05-07T10:00:00Z",
      "ended_at": "2026-05-07T10:05:00Z",
      "recording_url": "https://tavus.io/recordings/test123"
    }
  }'
```

**Expected result:** 200 OK, log message "Stored conversation: test_conv_001"

**Verify database insert:**
```bash
venv/bin/python -c "
from backend.models import Conversation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///conversations.db')
Session = sessionmaker(bind=engine)
session = Session()

conv = session.query(Conversation).filter_by(conversation_id='test_conv_001').first()

if conv:
    print(f'✓ Conversation ID: {conv.conversation_id}')
    print(f'✓ Visitor: {conv.visitor_name}')
    print(f'✓ Duration: {conv.duration_seconds}s')
    print(f'✓ Transcript length: {len(conv.transcript)} chars')
else:
    print('✗ Conversation not found')
"
```

**Test duplicate webhook (idempotency):**
```bash
# Send same webhook again
curl -X POST http://localhost:8001/webhooks/tavus \
  -H "Content-Type: application/json" \
  -d '{ ... same payload ... }'
```

**Expected result:** 200 OK, log message "Conversation test_conv_001 already exists"

### 3. API Endpoint Testing

**Test default query (7 days, newest):**
```bash
curl http://localhost:8001/api/conversations | jq .
```

**Expected output:**
```json
{
  "conversations": [
    {
      "id": 1,
      "conversation_id": "test_conv_001",
      "started_at": "2026-05-07T10:00:00Z",
      "duration_seconds": 300,
      "visitor_name": "John Smith",
      ...
    }
  ],
  "total": 1,
  "filters": {"days": "7", "sort": "newest"}
}
```

**Test time filtering:**
```bash
curl "http://localhost:8001/api/conversations?days=1" | jq '.total'
curl "http://localhost:8001/api/conversations?days=all" | jq '.total'
```

**Test sorting:**
```bash
curl "http://localhost:8001/api/conversations?sort=oldest" | jq '.conversations[0].started_at'
curl "http://localhost:8001/api/conversations?sort=longest" | jq '.conversations[0].duration_seconds'
```

**Test CSV export:**
```bash
curl "http://localhost:8001/api/conversations?format=csv" -o conversations.csv
cat conversations.csv
```

**Expected output:** CSV file with headers and conversation data

### 4. Frontend Testing

**Open browser:**
```bash
# Start server
./start.sh

# Open in browser
open http://localhost:8001/conversations
```

**Manual test checklist:**

- [ ] Page loads without errors
- [ ] Table displays test conversation
- [ ] "7 Days" filter button is active by default
- [ ] Click "1 Day" filter → table updates
- [ ] Click "All" filter → table updates
- [ ] Change sort to "Oldest First" → table reorders
- [ ] Change sort to "Longest Duration" → table reorders
- [ ] Click "View Transcript" → row expands with formatted conversation
- [ ] Click "Collapse" → row collapses
- [ ] Click "Recording" link → opens in new tab (if URL exists)
- [ ] Click "Export CSV" → downloads file
- [ ] Open CSV in spreadsheet → data is readable
- [ ] Test empty state: filter to "1 Day" with no recent conversations
- [ ] Check mobile responsiveness (resize browser)

### 5. End-to-End Flow

**Complete integration test:**

1. Start server: `./start.sh`
2. Open frontend: `http://localhost:8001/`
3. Create real Tavus conversation (click "Start Conversation")
4. Complete conversation naturally (have a full dialogue with avatar)
5. End conversation (close or let timeout)
6. Wait 30-60 seconds for Tavus to process and send webhook
7. Navigate to `http://localhost:8001/conversations`
8. Verify conversation appears in list
9. Click "View Transcript" → verify content matches actual conversation
10. Check visitor name extracted correctly (if mentioned)
11. Export CSV → verify format and content
12. Check `server.log` for webhook receipt and storage confirmation

### 6. Edge Cases

**Test error scenarios:**

- [ ] Send webhook with missing `conversation_id` → should log warning, return 200
- [ ] Send webhook with invalid timestamp format → should log error, return 200
- [ ] Send webhook with empty transcript array → should store empty JSON array
- [ ] Send webhook with no visitor name → `visitor_name` should be NULL
- [ ] Simulate database connection error → should return 500, log error
- [ ] API request with invalid `days` parameter → should fall back to default
- [ ] API request with invalid `sort` parameter → should fall back to default
- [ ] Frontend: network error during fetch → should show error message
- [ ] Frontend: malformed JSON in transcript → should skip record, log error

---

## Implementation Files

### New Files

1. **`backend/models.py`** — SQLAlchemy models and database initialization
2. **`frontend/conversations.html`** — Conversation history page UI
3. **`conversations.db`** — SQLite database file (generated on startup)
4. **`docs/superpowers/specs/2026-05-07-conversation-history-design.md`** — This document

### Modified Files

1. **`backend/app.py`** — Add:
   - Database initialization in startup event
   - Transcription storage logic in `/webhooks/tavus`
   - New GET `/api/conversations` endpoint
   - Serve `/conversations` HTML page

2. **`backend/requirements.txt`** — Add:
   - `sqlalchemy`

### Directory Structure

```
/home/swarocha/dev/tavus/
├── backend/
│   ├── app.py (modified)
│   ├── models.py (new)
│   ├── requirements.txt (modified)
│   ├── tavus_client.py
│   ├── tool_stubs.py
│   └── config.py
├── frontend/
│   ├── index.html
│   └── conversations.html (new)
├── conversations.db (new, generated)
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-07-conversation-history-design.md (new)
└── ...
```

---

## Security Considerations

**Data Privacy:**
- Conversation transcripts contain visitor information (names, unit numbers)
- Public `/conversations` route means anyone with URL can view all conversations
- Consider adding authentication for production deployment
- Consider data retention policy (auto-delete old conversations)

**XSS Prevention:**
- All user-provided data rendered via `textContent` (not the unsafe DOM property)
- Transcript content escaped before display
- If rich formatting needed later, use DOMPurify

**SQL Injection:**
- SQLAlchemy ORM prevents SQL injection
- All database queries use parameterized statements
- No raw SQL string concatenation

**Webhook Security:**
- Current implementation accepts all POST requests to `/webhooks/tavus`
- Production should validate webhook signature (Tavus documentation)
- Consider rate limiting to prevent abuse

---

## Future Enhancements

**Not in current scope, but possible extensions:**

1. **Authentication & Authorization**
   - Add admin login to protect `/conversations` route
   - Role-based access (view-only vs. export vs. delete)

2. **Search & Filtering**
   - Full-text search across transcripts
   - Filter by visitor name
   - Filter by conversation outcome (resolved, escalated, abandoned)

3. **Analytics Dashboard**
   - Average conversation duration
   - Most common visitor requests
   - Tool usage frequency
   - Peak conversation times

4. **Tool Usage Tracking**
   - Store which tools were called during conversation
   - Track tool success/failure rates
   - Link tool calls to conversation outcomes

5. **Escalation Tracking**
   - Flag conversations that escalated to human agent
   - Track escalation reasons and resolution
   - Human agent feedback on avatar performance

6. **Data Retention & Archival**
   - Auto-delete conversations older than N days
   - Archive to S3 or external storage
   - GDPR compliance (right to be forgotten)

7. **Export Formats**
   - PDF export with formatted transcripts
   - JSON export for programmatic access
   - Bulk export with date ranges

8. **Real-Time Updates**
   - WebSocket or SSE to push new conversations to frontend
   - Live conversation count
   - Notifications for escalations or errors

---

## Summary

This design adds persistent conversation storage to the Meridian AI concierge using SQLite and a web-based history viewer. The implementation:

- Captures conversation transcripts via Tavus webhook when conversation ends
- Stores metadata (timestamps, duration, visitor name, recording URL) in SQLite
- Provides REST API for querying with time-range filters and sorting
- Renders responsive web page at `/conversations` with expandable transcripts
- Supports CSV export for external analysis
- Uses safe DOM practices and SQLAlchemy ORM for security

The minimal approach leverages existing webhook infrastructure and SQLite's simplicity, making it fast to implement and easy to deploy. All requirements are met without over-engineering for hypothetical future needs.
