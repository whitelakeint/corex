# Knowledge Base Management Feature Design

**Date:** 2026-05-19  
**Status:** Approved  
**Author:** Claude Code

## Overview

A web-based admin interface for updating the building concierge knowledge base files. Admins authenticate with hardcoded credentials, edit knowledge base content in text areas, save changes to disk, and sync updates to the Tavus persona context.

## Requirements

- Admin can view current knowledge base content (building_info.txt, concierge_qa.txt)
- Admin can edit content inline via text areas
- Admin can save changes to disk
- Admin can trigger Tavus persona context sync
- Access protected by username/password authentication (admin/meridian)
- Session-based authentication with 2-hour expiration
- Clear success/error feedback for all operations

## Architecture

### Single-Page Admin Interface

**Route:** `/admin/knowledge-base`

The page conditionally renders based on authentication state:
- **Unauthenticated:** Login form with username/password fields
- **Authenticated:** Editor interface with two text areas, save button, and sync button

### Session Management

**In-memory session store:**
```python
_admin_sessions = {
    "session_id_uuid": {
        "username": "admin",
        "expires_at": datetime(...)
    }
}
```

**Session cookie:**
- Name: `admin_session`
- httpOnly: True
- Max-Age: 7200 seconds (2 hours)
- Path: `/admin`

**Session validation middleware:**
- Checks cookie presence
- Validates session ID exists in store
- Checks expiration timestamp
- Returns 401 if invalid/expired

### Components

#### Frontend: `frontend/admin-knowledge-base.html`

Single HTML file with:
- Embedded CSS for styling
- Embedded JavaScript for interactivity
- Conditional rendering (login form OR editor)
- Two text areas for knowledge base files
- Character count displays
- Action buttons (Save Files, Sync to Tavus, Logout)
- Status message area (success/error feedback)
- Safe DOM manipulation (no innerHTML)

#### Backend Endpoints

All endpoints added to `backend/app.py`:

1. **`GET /admin/knowledge-base`**
   - Serves the HTML page
   - No authentication check (client-side checks session)

2. **`POST /admin/auth`**
   - Request: `{username: str, password: str}`
   - Validates against hardcoded credentials (admin/meridian)
   - Creates session, sets httpOnly cookie
   - Response: `{status: "ok"}` or 401 with error

3. **`GET /admin/knowledge-base/content`** (protected)
   - Reads both knowledge base files from disk
   - Response: `{building_info: str, concierge_qa: str}`
   - Returns 401 if session invalid

4. **`POST /admin/knowledge-base/save`** (protected)
   - Request: `{building_info: str, concierge_qa: str}`
   - Validates content non-empty
   - Writes files to `knowledge-base/*.txt`
   - Response: `{status: "ok", message: "Files saved successfully"}`
   - Returns 400 for validation errors, 500 for file I/O errors

5. **`POST /admin/knowledge-base/sync`** (protected)
   - Reads current files from disk
   - Combines content (same logic as `update_persona_context.py`)
   - Calls `tavus_client.patch_persona()` with combined content
   - Response: `{status: "ok", message: "Tavus persona updated", chars: int}`
   - Returns 500 for Tavus API errors

6. **`POST /admin/logout`** (protected)
   - Removes session from store
   - Clears cookie
   - Response: `{status: "ok"}`

#### Session Management Code

```python
import secrets
from datetime import datetime, timedelta

# In-memory session store
_admin_sessions: dict[str, dict] = {}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "meridian"
SESSION_DURATION_SECONDS = 7200  # 2 hours

def create_session(username: str) -> str:
    """Create a new admin session and return session ID."""
    session_id = secrets.token_urlsafe(32)
    _admin_sessions[session_id] = {
        "username": username,
        "expires_at": datetime.utcnow() + timedelta(seconds=SESSION_DURATION_SECONDS),
    }
    return session_id

def validate_session(session_id: str) -> bool:
    """Check if session ID is valid and not expired."""
    if not session_id or session_id not in _admin_sessions:
        return False
    session = _admin_sessions[session_id]
    if datetime.utcnow() > session["expires_at"]:
        del _admin_sessions[session_id]
        return False
    return True

def destroy_session(session_id: str) -> None:
    """Remove session from store."""
    _admin_sessions.pop(session_id, None)
```

## Data Flow

### Initial Page Load

1. Browser → `GET /admin/knowledge-base`
2. Backend → serves HTML page
3. JavaScript → `GET /admin/knowledge-base/content`
4. If session valid → returns file contents, shows editor
5. If session invalid → returns 401, shows login form

### Login Flow

1. User enters credentials → clicks "Login"
2. JavaScript → `POST /admin/auth` with `{username, password}`
3. Backend validates credentials
4. On success → creates session, sets cookie, returns `{status: "ok"}`
5. JavaScript → fetches content, transitions to editor view
6. On failure → returns 401, shows error message

### Save Flow

1. User edits content → clicks "Save Files"
2. JavaScript → `POST /admin/knowledge-base/save` with file contents
3. Backend validates session, checks non-empty, writes to disk
4. Returns success message
5. JavaScript displays confirmation

### Sync Flow

1. User clicks "Sync to Tavus"
2. JavaScript → `POST /admin/knowledge-base/sync`
3. Backend reads files, combines content, calls Tavus API
4. Returns success with character count
5. JavaScript displays confirmation

### Session Expiration

1. Any protected endpoint returns 401 if session expired
2. JavaScript detects 401 → clears editor, shows login form
3. Displays "Session expired" message

## Error Handling

### Authentication Errors

- Invalid credentials → 401: `{error: "Invalid username or password"}`
- Missing session → 401: `{error: "Authentication required"}`
- Expired session → 401: `{error: "Session expired, please login again"}`

### Validation Errors

- Empty content → 400: `{error: "Content cannot be empty"}`
- Missing fields → 400: `{error: "Missing required field: building_info"}`
- Malformed JSON → 400: `{error: "Invalid JSON format"}`

### File System Errors

- Read failure → 500: `{error: "Failed to read knowledge base files"}`
- Write failure → 500: `{error: "Failed to save files: [reason]"}`
- Permission denied → 500: `{error: "Permission denied writing to knowledge-base/"}`

### Tavus API Errors

- API failure → 500: `{error: "Tavus API error: [reason]"}`
- Network timeout → 500: `{error: "Tavus API timeout"}`
- Invalid persona ID → 500: `{error: "Invalid TAVUS_PERSONA_ID configuration"}`

### Frontend Error Display

- Errors shown in red message box at top of page
- Success messages shown in green
- Auto-dismiss after 5 seconds
- Manual dismiss button (×)

### Logging

All operations logged with:
- Timestamp
- Username (for authenticated operations)
- Action (login, save, sync)
- Result (success/failure)
- Error details (if applicable)

## Security Considerations

- Hardcoded credentials (admin/meridian) stored as constants in code
- httpOnly session cookies prevent JavaScript access
- Sessions expire after 2 hours of inactivity
- All admin endpoints check session validity
- No password stored in session (only username)
- Sessions stored in memory (cleared on server restart)

**Production Considerations (not implemented in initial version):**
- Use environment variables for credentials
- Hash passwords instead of plaintext comparison
- Use HTTPS to protect credentials in transit
- Add rate limiting on auth endpoint
- Persistent session storage (Redis/database)
- CSRF token protection

## Testing

### Manual Testing Checklist

**Authentication:**
- [ ] Correct credentials → successful login
- [ ] Incorrect credentials → error message
- [ ] Session persists across page refresh
- [ ] Session expires after 2 hours → login required

**Editor:**
- [ ] Text areas populated with current content
- [ ] Character counts update as user types
- [ ] Content editable in both text areas

**Save Operation:**
- [ ] Modified content saves to disk
- [ ] Files on disk match textarea content
- [ ] Success message displays
- [ ] Empty content rejected with error

**Sync Operation:**
- [ ] Tavus persona context updates
- [ ] Success message shows character count
- [ ] Sync after save uses new content
- [ ] Sync without save uses disk content

**Error Scenarios:**
- [ ] Session expired → redirects to login
- [ ] Tavus API error → error message displays
- [ ] File write error → error message displays

**Security:**
- [ ] Cannot access endpoints without session
- [ ] Session cookie is httpOnly
- [ ] Logout clears session

### Browser Testing

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Mobile responsive not required (admin tool)

## Files to Create

1. `frontend/admin-knowledge-base.html` - Admin interface page
2. Session management code in `backend/app.py`
3. Six new endpoints in `backend/app.py`

## Files to Modify

- `backend/app.py` - Add session store, endpoints, helper functions

## Dependencies

No new dependencies required. Uses existing:
- FastAPI (routing, request/response)
- Pydantic (request validation)
- `backend/tavus_client.py` (Tavus API calls)
- Standard library (secrets, datetime, pathlib)

## Implementation Notes

- Reuse logic from `scripts/update_persona_context.py` for Tavus sync
- Follow existing patterns in `backend/app.py` (Pydantic models, logging)
- Follow frontend patterns from `conversations.html` (vanilla JS, safe DOM)
- Session cleanup on server restart is acceptable (in-memory store)
- Character count helps admin validate content before sync
- Sync is separate from save to allow validation before pushing to Tavus

## Future Enhancements (Out of Scope)

- Multiple knowledge base files (dynamic list)
- File upload instead of text area editing
- Version history / rollback
- Multi-user support with different permissions
- Audit log / change tracking
- Preview changes before save
- Syntax highlighting for structured content
- Auto-save drafts
- Compare current vs. Tavus-synced content
