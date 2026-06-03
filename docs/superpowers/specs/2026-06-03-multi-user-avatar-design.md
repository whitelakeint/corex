# Multi-User Avatar System Design

**Date:** 2026-06-03  
**Status:** Approved  
**Author:** Claude Code

## Overview

Add a second user (buildingB) with separate Tavus avatar and knowledge base files. Users select their identity at login, which determines which persona and KB content to use.

## Requirements

- Two users: `admin` and `buildingB`
- Both use same password: `meridian`
- Each user has separate:
  - Tavus persona (different avatar appearance)
  - Knowledge base directory
  - Replica ID
- Simple dropdown selection at login
- KB management page loads user-specific files
- No database schema changes
- Day one implementation - keep it simple

## Architecture

### User Configuration

Hardcoded user mapping in `backend/config.py`:

```python
USERS = {
    "admin": {
        "password": "meridian",
        "persona_id": os.getenv("ADMIN_PERSONA_ID", "p5c2370d05ad"),
        "replica_id": os.getenv("ADMIN_REPLICA_ID", "r1af76e94d00"),
        "kb_path": "knowledge-base/admin"
    },
    "buildingB": {
        "password": "meridian",
        "persona_id": os.getenv("BUILDINGB_PERSONA_ID", ""),
        "replica_id": "r90bbd427f71",
        "kb_path": "knowledge-base/buildingB"
    }
}
```

### Environment Variables

New variables in `.env`:

```bash
# Admin user (existing persona)
ADMIN_PERSONA_ID=p5c2370d05ad
ADMIN_REPLICA_ID=r1af76e94d00

# BuildingB user (new persona to be created)
BUILDINGB_PERSONA_ID=<run setup_persona.py to get this>
BUILDINGB_REPLICA_ID=r90bbd427f71
```

### Knowledge Base Structure

```
knowledge-base/
  admin/                    # Migrated from existing KB files
    building_info.txt
    concierge_qa.txt
  buildingB/                # New KB for buildingB
    building_info.txt       # Dummy content for Building B
    concierge_qa.txt        # Dummy Q&A for Building B
```

## Components

### Frontend Changes (`frontend/index.html`)

**Login Form:**
- Add dropdown/select before username field
- Options: "admin" or "buildingB"
- Pre-fill username field based on selection
- Password field remains (same for both: "meridian")

**SessionStorage:**
- Store `currentUser` after login
- Read from sessionStorage on page load
- Clear on logout

**Conversation Creation:**
- Pass `username` in POST body to `/api/conversations`

**KB Management:**
- Detect username from sessionStorage
- Pass as query param to KB endpoints: `?user=admin`

### Backend Changes (`backend/app.py`)

**User Validation:**
```python
def validate_user(username: str, password: str) -> bool:
    """Validate username and password against USERS dict."""
    if username not in USERS:
        return False
    return USERS[username]["password"] == password

def get_user_config(username: str) -> dict:
    """Get user configuration."""
    if username not in USERS:
        raise ValueError(f"Unknown user: {username}")
    return USERS[username]
```

**Conversation Endpoint Modification:**
```python
@app.post("/api/conversations")
async def create_conversation(request: Request):
    body = await request.json()
    username = body.get("username", "admin")  # Default to admin for backward compat
    
    user_config = get_user_config(username)
    persona_id = user_config["persona_id"]
    
    if not persona_id:
        return JSONResponse(
            status_code=500,
            content={"error": f"Persona not configured for {username}. Run setup_persona.py."}
        )
    
    data = await tavus_client.create_conversation(
        persona_id=persona_id,
        properties={...}
    )
    # Store username in conversation record (optional)
    return JSONResponse(content=data)
```

**KB Endpoints Modification:**

All KB endpoints (`/admin/knowledge-base/content`, `/admin/knowledge-base/save`, `/admin/knowledge-base/sync`) accept `user` query parameter:

```python
@app.get("/admin/knowledge-base/content")
async def get_kb_content(user: str = "admin"):
    user_config = get_user_config(user)
    kb_path = Path(user_config["kb_path"])
    
    building_info = (kb_path / "building_info.txt").read_text()
    concierge_qa = (kb_path / "concierge_qa.txt").read_text()
    
    return {
        "building_info": building_info,
        "concierge_qa": concierge_qa
    }
```

### Persona Creation Script

Modify `scripts/setup_persona.py` to accept command-line arguments:

```bash
# Create buildingB persona
python -m scripts.setup_persona --user buildingB --replica r90bbd427f71
```

Script reads user config from `config.USERS`, creates persona with:
- User-specific replica_id
- User-specific system prompt (loaded from KB files)
- Returns persona_id to add to .env

## Data Flow

### Login Flow

1. User selects "buildingB" from dropdown
2. Form pre-fills username field with "buildingB"
3. User enters password "meridian"
4. Frontend validates locally (checks username in hardcoded list)
5. Store `currentUser = "buildingB"` in sessionStorage
6. Transition to app screen

### Conversation Creation Flow

1. User clicks "Start Conversation"
2. Frontend sends: `POST /api/conversations` with `{username: "buildingB"}`
3. Backend looks up `USERS["buildingB"]["persona_id"]`
4. Creates Tavus conversation with buildingB's persona
5. Returns conversation_url
6. Frontend loads Daily iframe with buildingB avatar

### KB Management Flow

1. User clicks "Update KB" button
2. Frontend detects `currentUser` from sessionStorage
3. Sends: `GET /admin/knowledge-base/content?user=buildingB`
4. Backend reads from `knowledge-base/buildingB/` directory
5. User edits content
6. Save: `POST /admin/knowledge-base/save?user=buildingB`
7. Backend writes to `knowledge-base/buildingB/` files
8. Sync: `POST /admin/knowledge-base/sync?user=buildingB`
9. Backend syncs to buildingB's persona

## Error Handling

### Authentication Errors

- Invalid username → Show error: "Invalid username or password"
- Invalid password → Show error: "Invalid username or password"
- Both use same frontend validation as current login

### Configuration Errors

- Missing persona_id → 500: "Persona not configured for {username}. Run setup_persona.py with --user {username}"
- Missing replica_id → 500: "Replica not configured for {username}"
- Invalid user in request → 400: "Unknown user: {username}"

### KB Errors

- KB directory doesn't exist → Auto-create on first access
- File doesn't exist → Return empty string, auto-create on save
- File read error → 500: "Failed to load knowledge base for {username}"

### Backward Compatibility

- If no username provided in request → default to "admin"
- Existing sessions remain valid (no forced logout)
- Frontend gracefully handles missing sessionStorage (defaults to admin)

## Migration Steps

1. **Move existing KB files:**
   ```bash
   mkdir -p knowledge-base/admin
   mv knowledge-base/building_info.txt knowledge-base/admin/
   mv knowledge-base/concierge_qa.txt knowledge-base/admin/
   ```

2. **Create buildingB KB directory:**
   ```bash
   mkdir -p knowledge-base/buildingB
   ```

3. **Create dummy KB content for buildingB:**
   - `knowledge-base/buildingB/building_info.txt` - short dummy building info
   - `knowledge-base/buildingB/concierge_qa.txt` - short dummy Q&A

4. **Update .env:**
   ```bash
   # Rename existing var
   TAVUS_PERSONA_ID → ADMIN_PERSONA_ID
   
   # Add new vars
   ADMIN_REPLICA_ID=r1af76e94d00
   BUILDINGB_PERSONA_ID=<empty for now>
   BUILDINGB_REPLICA_ID=r90bbd427f71
   ```

5. **Create buildingB persona:**
   ```bash
   python -m scripts.setup_persona --user buildingB --replica r90bbd427f71
   # Copy returned persona_id to .env as BUILDINGB_PERSONA_ID
   ```

6. **Test both users:**
   - Login as admin → verify conversation + KB
   - Login as buildingB → verify conversation + KB

## Files to Create

1. `knowledge-base/buildingB/building_info.txt` - dummy content
2. `knowledge-base/buildingB/concierge_qa.txt` - dummy content
3. Modified `scripts/setup_persona.py` - add CLI args for user/replica

## Files to Modify

1. `backend/config.py` - add USERS dict, new env vars
2. `backend/app.py` - modify conversation + KB endpoints
3. `frontend/index.html` - add user dropdown, sessionStorage logic
4. `.env` - add new persona/replica vars

## Testing

### Manual Testing Checklist

**Admin User:**
- [ ] Select "admin" from dropdown
- [ ] Login with password "meridian"
- [ ] Start conversation → admin avatar appears
- [ ] Check KB page → shows admin's files
- [ ] Edit and save KB → admin files updated
- [ ] Sync → admin persona updated

**BuildingB User:**
- [ ] Select "buildingB" from dropdown
- [ ] Login with password "meridian"
- [ ] Start conversation → buildingB avatar appears (different from admin)
- [ ] Check KB page → shows buildingB's files
- [ ] Edit and save KB → buildingB files updated
- [ ] Sync → buildingB persona updated

**Isolation:**
- [ ] Login as buildingB, edit KB content
- [ ] Logout, login as admin
- [ ] Verify admin KB unchanged
- [ ] Start conversations as each user
- [ ] Verify different personas/avatars appear

**Error Cases:**
- [ ] Invalid username → error message
- [ ] BuildingB persona not created → error message
- [ ] Missing KB files → auto-created

## Future Enhancements (Out of Scope)

- Database storage of users (instead of hardcoded)
- Different passwords per user
- More than 2 users
- User management UI
- Conversation history filtered by user
- User roles/permissions
- Password hashing
- Session security improvements

## Implementation Notes

- Keep it simple for day one - hardcoded config is fine
- Frontend validation prevents bad usernames reaching backend
- Default to "admin" for backward compatibility
- Auto-create KB directories on first access
- Script modification is minimal - just add CLI arg parsing
- No database changes needed
- Existing conversation history works as-is (no user tracking yet)
