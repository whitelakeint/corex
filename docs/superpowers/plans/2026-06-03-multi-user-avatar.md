# Multi-User Avatar System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add second user (buildingB) with separate Tavus avatar and knowledge base, selectable at login.

**Architecture:** Hardcoded user mapping in config (admin/buildingB), frontend dropdown for user selection, backend routes use username to select persona_id and KB directory path.

**Tech Stack:** Python (FastAPI), JavaScript (vanilla), Tavus API

---

## File Structure

**New files:**
- `knowledge-base/admin/building_info.txt` - migrated from root
- `knowledge-base/admin/concierge_qa.txt` - migrated from root
- `knowledge-base/buildingB/building_info.txt` - dummy content
- `knowledge-base/buildingB/concierge_qa.txt` - dummy Q&A

**Modified files:**
- `backend/config.py` - add USERS dict, new env vars
- `backend/app.py` - add user validation, modify conversation/KB endpoints
- `frontend/index.html` - add user dropdown, sessionStorage logic
- `scripts/setup_persona.py` - add CLI args for user/replica
- `.env` - add admin/buildingB persona/replica vars

---

### Task 1: Migrate Existing KB Files

**Files:**
- Move: `knowledge-base/building_info.txt` → `knowledge-base/admin/building_info.txt`
- Move: `knowledge-base/concierge_qa.txt` → `knowledge-base/admin/concierge_qa.txt`

- [ ] **Step 1: Create admin KB directory**

```bash
mkdir -p knowledge-base/admin
```

Expected: Directory created

- [ ] **Step 2: Move existing KB files to admin directory**

```bash
mv knowledge-base/building_info.txt knowledge-base/admin/
mv knowledge-base/concierge_qa.txt knowledge-base/admin/
```

Expected: Files moved, `knowledge-base/admin/` contains both files

- [ ] **Step 3: Verify files moved**

```bash
ls -la knowledge-base/admin/
```

Expected: Shows `building_info.txt` and `concierge_qa.txt`

- [ ] **Step 4: Commit migration**

```bash
git add knowledge-base/
git commit -m "refactor: migrate KB files to admin subdirectory"
```

---

### Task 2: Create BuildingB KB Files

**Files:**
- Create: `knowledge-base/buildingB/building_info.txt`
- Create: `knowledge-base/buildingB/concierge_qa.txt`

- [ ] **Step 1: Create buildingB KB directory**

```bash
mkdir -p knowledge-base/buildingB
```

Expected: Directory created

- [ ] **Step 2: Write dummy building info**

Create `knowledge-base/buildingB/building_info.txt`:

```text
# Building B Information

**Location:** 5678 Oak Street, Downtown District

**Building Type:** Modern residential tower with commercial ground floor

**Units:** 75 apartments across 10 floors
- Studios: $1,800/month
- 1BR: $2,400/month
- 2BR: $3,200/month

**Amenities:**
- Rooftop terrace (10th floor)
- Fitness center (ground floor)
- Co-working space (2nd floor)
- Bike storage (basement level)
- Pet-friendly with dog park

**Office Hours:**
- Leasing Office: Mon-Fri 9 AM - 6 PM, Sat 10 AM - 4 PM
- Contact: leasing@buildingb.com | (555) 234-5678

**Parking:** Underground garage, $150/month per space

**Pet Policy:** Dogs and cats welcome (2 pets max, 50 lbs weight limit), $50/month pet fee
```

- [ ] **Step 3: Write dummy Q&A**

Create `knowledge-base/buildingB/concierge_qa.txt`:

```text
# Building B Concierge Q&A

## Visitor Access
Q: "I'm here to see a resident."
A: "Great! Please provide the resident's name and apartment number, and I'll notify them of your arrival."

Q: "How do I get buzzed in after hours?"
A: "After 6 PM, use the callbox at the main entrance. Enter the apartment number and press 'Call' to reach the resident directly."

## Leasing
Q: "Are there any units available?"
A: "Yes! We have studios starting at $1,800, 1-bedrooms at $2,400, and 2-bedrooms at $3,200. Would you like to schedule a tour?"

Q: "What's included in the rent?"
A: "Rent includes water, trash, and access to all building amenities. Electricity and internet are resident-paid."

## Amenities
Q: "Where's the gym?"
A: "Our fitness center is on the ground floor, just past the lobby. It's open 24/7 for residents."

Q: "Do you have a pool?"
A: "We don't have a pool, but we have a beautiful rooftop terrace on the 10th floor with seating and city views."

## Packages
Q: "I'm delivering a package."
A: "Please bring packages to the front desk. I'll log it and notify the resident. What's the recipient's apartment number?"

## Pets
Q: "Are pets allowed?"
A: "Yes! We're pet-friendly. Dogs and cats are welcome with a $50/month pet fee. Maximum 2 pets, 50 lbs weight limit."
```

- [ ] **Step 4: Verify files created**

```bash
ls -la knowledge-base/buildingB/
cat knowledge-base/buildingB/building_info.txt | head -5
```

Expected: Both files exist, content visible

- [ ] **Step 5: Commit buildingB KB files**

```bash
git add knowledge-base/buildingB/
git commit -m "feat: add buildingB knowledge base with dummy content"
```

---

### Task 3: Update Backend Config

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Add USERS dict to config.py**

Add after line 14 (after `ADMIN_PASSWORD` definition):

```python
# Multi-user configuration
USERS = {
    "admin": {
        "password": "meridian",
        "persona_id": os.getenv("ADMIN_PERSONA_ID", os.getenv("TAVUS_PERSONA_ID", "")),
        "replica_id": os.getenv("ADMIN_REPLICA_ID", TAVUS_REPLICA_ID),
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

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile backend/config.py
```

Expected: No errors

- [ ] **Step 3: Test config import**

```bash
python -c "from backend.config import USERS; print(USERS.keys())"
```

Expected: `dict_keys(['admin', 'buildingB'])`

- [ ] **Step 4: Commit config changes**

```bash
git add backend/config.py
git commit -m "feat: add multi-user configuration to config.py"
```

---

### Task 4: Add User Validation Functions

**Files:**
- Modify: `backend/app.py` (add after imports, before app initialization)

- [ ] **Step 1: Import USERS from config**

Add to imports section (after line 23):

```python
from backend.config import BACKEND_URL, TAVUS_PERSONA_ID, ADMIN_USERNAME, ADMIN_PASSWORD, USERS
```

- [ ] **Step 2: Add validate_user function**

Add after line 75 (after `destroy_session` function):

```python
def validate_user(username: str, password: str) -> bool:
    """Validate username and password against USERS dict."""
    if username not in USERS:
        return False
    return USERS[username]["password"] == password


def get_user_config(username: str) -> dict:
    """Get user configuration.
    
    Args:
        username: Username to look up
        
    Returns:
        User config dict with persona_id, replica_id, kb_path
        
    Raises:
        ValueError: If username not found
    """
    if username not in USERS:
        raise ValueError(f"Unknown user: {username}")
    return USERS[username]
```

- [ ] **Step 3: Verify syntax**

```bash
python -m py_compile backend/app.py
```

Expected: No errors

- [ ] **Step 4: Test user validation**

```bash
python -c "from backend.app import validate_user; print(validate_user('admin', 'meridian'))"
```

Expected: `True`

- [ ] **Step 5: Commit validation functions**

```bash
git add backend/app.py
git commit -m "feat: add user validation functions"
```

---

### Task 5: Modify Conversation Endpoint

**Files:**
- Modify: `backend/app.py` - `/api/conversations` endpoint

- [ ] **Step 1: Update create_conversation endpoint**

Find the `@app.post("/api/conversations")` function (around line 150) and replace with:

```python
@app.post("/api/conversations")
async def create_conversation(request: Request):
    """Create a new Tavus conversation for the specified user.
    
    Request body:
        {
            "username": "admin" | "buildingB"  (optional, defaults to "admin")
        }
    """
    body = await request.json()
    username = body.get("username", "admin")
    
    try:
        user_config = get_user_config(username)
    except ValueError as e:
        logger.error(f"Invalid user in conversation request: {username}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    
    persona_id = user_config["persona_id"]
    
    if not persona_id:
        logger.error(f"Persona not configured for user: {username}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Persona not configured for {username}. Run setup_persona.py with --user {username}"}
        )

    data = await tavus_client.create_conversation(
        persona_id=persona_id,
        properties={
            "max_call_duration": 600,
            "participant_left_timeout": 30,
            "enable_recording": True,
            "enable_transcription": True,
            "apply_greenscreen": False,
        },
        callback_url=f"{BACKEND_URL}/webhooks/tavus",
    )

    conversation_id = data.get("conversation_id")
    conversation_url = data.get("conversation_url")

    if not conversation_id or not conversation_url:
        logger.error(f"Tavus API returned incomplete response: {data}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to create conversation: incomplete response from Tavus"}
        )

    logger.info(f"Conversation created for user {username}: {conversation_id}")
    return JSONResponse(content=data)
```

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile backend/app.py
```

Expected: No errors

- [ ] **Step 3: Commit conversation endpoint changes**

```bash
git add backend/app.py
git commit -m "feat: modify conversation endpoint to support multi-user"
```

---

### Task 6: Modify KB Content Endpoint

**Files:**
- Modify: `backend/app.py` - `/admin/knowledge-base/content` endpoint

- [ ] **Step 1: Update get_kb_content endpoint**

Find the `@app.get("/admin/knowledge-base/content")` function and replace with:

```python
@app.get("/admin/knowledge-base/content")
async def get_kb_content(user: str = "admin"):
    """Get current knowledge base file contents for specified user.
    
    Query params:
        user: Username (admin or buildingB), defaults to admin
    """
    try:
        user_config = get_user_config(user)
    except ValueError as e:
        logger.error(f"Invalid user in KB content request: {user}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    
    kb_base = FRONTEND_DIR.parent / user_config["kb_path"]
    building_info_path = kb_base / "building_info.txt"
    concierge_qa_path = kb_base / "concierge_qa.txt"
    
    # Auto-create directory if doesn't exist
    kb_base.mkdir(parents=True, exist_ok=True)
    
    try:
        building_info = building_info_path.read_text() if building_info_path.exists() else ""
        concierge_qa = concierge_qa_path.read_text() if concierge_qa_path.exists() else ""
        logger.info(f"Knowledge base content retrieved for user: {user}")
        return {
            "building_info": building_info,
            "concierge_qa": concierge_qa,
        }
    except Exception as e:
        logger.error(f"Failed to read KB files for {user}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to load knowledge base for {user}"}
        )
```

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile backend/app.py
```

Expected: No errors

- [ ] **Step 3: Commit KB content endpoint changes**

```bash
git add backend/app.py
git commit -m "feat: modify KB content endpoint to support multi-user"
```

---

### Task 7: Modify KB Save Endpoint

**Files:**
- Modify: `backend/app.py` - `/admin/knowledge-base/save` endpoint

- [ ] **Step 1: Add Pydantic model for save request**

Find the existing `SaveKBRequest` model (should be near other Pydantic models) and add user field:

```python
class SaveKBRequest(BaseModel):
    building_info: str
    concierge_qa: str
    user: str = "admin"  # Add this line
```

- [ ] **Step 2: Update save_kb endpoint**

Find the `@app.post("/admin/knowledge-base/save")` function and replace with:

```python
@app.post("/admin/knowledge-base/save")
async def save_kb(request: SaveKBRequest):
    """Save knowledge base files for specified user.
    
    Request body:
        {
            "building_info": "...",
            "concierge_qa": "...",
            "user": "admin" | "buildingB"  (optional, defaults to admin)
        }
    """
    try:
        user_config = get_user_config(request.user)
    except ValueError as e:
        logger.error(f"Invalid user in KB save request: {request.user}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    
    if not request.building_info.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Building information cannot be empty"}
        )
    
    if not request.concierge_qa.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Concierge Q&A cannot be empty"}
        )
    
    kb_base = FRONTEND_DIR.parent / user_config["kb_path"]
    building_info_path = kb_base / "building_info.txt"
    concierge_qa_path = kb_base / "concierge_qa.txt"
    
    # Auto-create directory if doesn't exist
    kb_base.mkdir(parents=True, exist_ok=True)
    
    try:
        building_info_path.write_text(request.building_info)
        concierge_qa_path.write_text(request.concierge_qa)
        logger.info(f"Knowledge base files saved for user: {request.user}")
        return {"status": "ok", "message": "Files saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save KB files for {request.user}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save files: {str(e)}"}
        )
```

- [ ] **Step 3: Verify syntax**

```bash
python -m py_compile backend/app.py
```

Expected: No errors

- [ ] **Step 4: Commit KB save endpoint changes**

```bash
git add backend/app.py
git commit -m "feat: modify KB save endpoint to support multi-user"
```

---

### Task 8: Modify KB Sync Endpoint

**Files:**
- Modify: `backend/app.py` - `/admin/knowledge-base/sync` endpoint

- [ ] **Step 1: Update sync_kb endpoint**

Find the `@app.post("/admin/knowledge-base/sync")` function and replace with:

```python
@app.post("/admin/knowledge-base/sync")
async def sync_kb(request: Request):
    """Sync knowledge base to Tavus persona for specified user.
    
    Query params:
        user: Username (admin or buildingB), defaults to admin
    """
    params = request.query_params
    user = params.get("user", "admin")
    
    try:
        user_config = get_user_config(user)
    except ValueError as e:
        logger.error(f"Invalid user in KB sync request: {user}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    
    persona_id = user_config["persona_id"]
    
    if not persona_id:
        logger.error(f"Persona not configured for user: {user}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Persona not configured for {user}. Run setup_persona.py with --user {user}"}
        )
    
    kb_base = FRONTEND_DIR.parent / user_config["kb_path"]
    building_info_path = kb_base / "building_info.txt"
    concierge_qa_path = kb_base / "concierge_qa.txt"
    
    try:
        building_info = building_info_path.read_text()
        concierge_qa = concierge_qa_path.read_text()
    except Exception as e:
        logger.error(f"Failed to read KB files for sync (user: {user}): {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to read knowledge base files for {user}"}
        )
    
    combined_context = f"{building_info}\n\n---\n\n{concierge_qa}"
    char_count = len(combined_context)
    
    operations = [
        {"op": "replace", "path": "/context", "value": combined_context}
    ]
    
    try:
        result = await tavus_client.patch_persona(persona_id, operations)
        logger.info(f"Tavus persona updated for user {user}: {char_count} chars")
        return {
            "status": "ok",
            "message": "Tavus persona updated",
            "chars": char_count
        }
    except Exception as e:
        logger.error(f"Tavus API error during sync (user: {user}): {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Tavus API error: {str(e)}"}
        )
```

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile backend/app.py
```

Expected: No errors

- [ ] **Step 3: Commit KB sync endpoint changes**

```bash
git add backend/app.py
git commit -m "feat: modify KB sync endpoint to support multi-user"
```

---

### Task 9: Add User Dropdown to Login Form

**Files:**
- Modify: `frontend/index.html` - login form section

- [ ] **Step 1: Add user dropdown to login form**

Find the login form (around line 593) and add a dropdown before the username field. Replace the username field section with:

```html
      <div class="login-field">
        <label for="login-userselect">Building</label>
        <select id="login-userselect" style="width: 100%; padding: 0.8rem 1rem; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(201, 169, 110, 0.15); border-radius: 2px; color: var(--login-text); font-family: 'DM Sans', sans-serif; font-size: 0.95rem; outline: none; cursor: pointer;">
          <option value="admin">Admin / Meridian Building</option>
          <option value="buildingB">Building B</option>
        </select>
      </div>
      <div class="login-field">
        <label for="login-user">Username</label>
        <input type="text" id="login-user" placeholder="Enter username" readonly style="background: rgba(255, 255, 255, 0.02);" />
      </div>
```

- [ ] **Step 2: Add dropdown change handler**

In the JavaScript section (around line 686), add after the loginPass variable definition:

```javascript
  const loginUserSelect = document.getElementById("login-userselect");
  
  // Pre-fill username based on dropdown selection
  function updateUsernameField() {
    loginUser.value = loginUserSelect.value;
  }
  
  // Initialize on page load
  updateUsernameField();
  
  // Update on dropdown change
  loginUserSelect.addEventListener("change", updateUsernameField);
```

- [ ] **Step 3: Verify HTML syntax**

```bash
python -c "from html.parser import HTMLParser; HTMLParser().feed(open('frontend/index.html').read()); print('Valid HTML')"
```

Expected: "Valid HTML" or no errors

- [ ] **Step 4: Commit login dropdown changes**

```bash
git add frontend/index.html
git commit -m "feat: add user dropdown to login form"
```

---

### Task 10: Add SessionStorage Logic

**Files:**
- Modify: `frontend/index.html` - login and logout JavaScript

- [ ] **Step 1: Store username in sessionStorage on login**

Find the login form submit handler (around line 725) and modify the success block to store username:

```javascript
    if (user === VALID_USER && pass === VALID_PASS) {
      // Set session cookie — expires in 7 days
      var expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toUTCString();
      document.cookie = "concierge_session=1; expires=" + expires + "; path=/; SameSite=Strict";
      
      // Store current user in sessionStorage
      sessionStorage.setItem("currentUser", user);

      loginError.classList.remove("visible");
      loginScreen.classList.add("hidden");
      setTimeout(() => {
        loginScreen.style.display = "none";
        appScreen.classList.add("visible");
      }, 600);
    } else {
```

- [ ] **Step 2: Clear sessionStorage on logout**

Find the logout() function (around line 751) and add sessionStorage clear:

```javascript
  function logout() {
    // End any active conversation first
    if (conversationId) {
      fetch(API_BASE + "/api/conversations/" + conversationId + "/end", {
        method: "POST",
      }).catch(() => {});
    }

    // Clean up everything
    endEverything();

    cardBody.classList.remove("has-iframe");
    welcome.style.display = "block";
    actions.style.display = "flex";
    actions.style.padding = "";
    btnStart.style.display = "inline-block";
    btnStart.disabled = false;
    btnEnd.style.display = "none";
    btnEnd.disabled = false;
    conversationId = null;
    clearError();
    setStatus("Ready", "");

    // Clear session cookie and sessionStorage
    document.cookie = "concierge_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Strict";
    sessionStorage.removeItem("currentUser");
```

- [ ] **Step 3: Restore username from sessionStorage on page load**

Add after the hasSession check (around line 698):

```javascript
  if (hasSession && !resumeConversationId) {
    console.log("[Session] Existing session found, skipping login");
    
    // Restore username from sessionStorage if available
    var storedUser = sessionStorage.getItem("currentUser");
    if (storedUser && (storedUser === "admin" || storedUser === "buildingB")) {
      loginUserSelect.value = storedUser;
      updateUsernameField();
    }
    
    loginScreen.style.display = "none";
    appScreen.classList.add("visible");
  }
```

- [ ] **Step 4: Commit sessionStorage logic**

```bash
git add frontend/index.html
git commit -m "feat: add sessionStorage logic for user persistence"
```

---

### Task 11: Pass Username in Conversation Request

**Files:**
- Modify: `frontend/index.html` - btnStart click handler

- [ ] **Step 1: Modify conversation creation to send username**

Find the btnStart event listener (around line 815) and modify the fetch call:

```javascript
    try {
      var username = sessionStorage.getItem("currentUser") || "admin";
      
      const res = await fetch(API_BASE + "/api/conversations", { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username })
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Server error " + res.status);
      }
```

- [ ] **Step 2: Verify JavaScript syntax**

```bash
node -c frontend/index.html 2>&1 | grep -i error || echo "No JS syntax errors"
```

Expected: "No JS syntax errors"

- [ ] **Step 3: Commit conversation request changes**

```bash
git add frontend/index.html
git commit -m "feat: pass username in conversation creation request"
```

---

### Task 12: Pass Username to KB Management Page

**Files:**
- Modify: `frontend/index.html` - Update KB button click handler
- Modify: `frontend/admin-knowledge-base.html` - KB API calls

- [ ] **Step 1: Modify Update KB button to pass username**

In `frontend/index.html`, find the "Update KB" button (around line 619) and modify:

```html
      <button id="btn-kb" onclick="navigateToKB()" style="background: rgba(255, 255, 255, 0.1); color: #fff; border: 1px solid rgba(255, 255, 255, 0.2); padding: 0.5rem 1rem; font-size: 0.8rem; border-radius: 6px; cursor: pointer; margin-right: 0.5rem;">Update KB</button>
```

And add the function in the script section (before the logout button handler):

```javascript
  function navigateToKB() {
    var username = sessionStorage.getItem("currentUser") || "admin";
    window.location.href = "/admin/knowledge-base?user=" + username;
  }
```

- [ ] **Step 2: Modify KB page to read username from URL**

In `frontend/admin-knowledge-base.html`, add at the top of the script section (around line 224):

```javascript
        let currentUser = "admin";
        
        // Read user from URL query param
        const urlParams = new URLSearchParams(window.location.search);
        const userParam = urlParams.get("user");
        if (userParam && (userParam === "admin" || userParam === "buildingB")) {
            currentUser = userParam;
        }
```

- [ ] **Step 3: Modify KB loadContent to use currentUser**

In `frontend/admin-knowledge-base.html`, find the loadContent function (around line 232) and modify:

```javascript
        async function loadContent() {
            try {
                const response = await fetch('/admin/knowledge-base/content?user=' + currentUser);
                if (response.ok) {
```

- [ ] **Step 4: Modify KB handleSave to use currentUser**

In `frontend/admin-knowledge-base.html`, find the handleSave function (around line 314) and modify:

```javascript
            try {
                const response = await fetch('/admin/knowledge-base/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        building_info: buildingInfo,
                        concierge_qa: conciergeQa,
                        user: currentUser
                    }),
                });
```

- [ ] **Step 5: Modify KB handleSync to use currentUser**

In `frontend/admin-knowledge-base.html`, find the handleSync function (around line 338) and modify:

```javascript
            try {
                const response = await fetch('/admin/knowledge-base/sync?user=' + currentUser, {
                    method: 'POST',
                });
```

- [ ] **Step 6: Update KB page title to show current user**

In `frontend/admin-knowledge-base.html`, modify the page title display (around line 190):

```html
        <h1>Knowledge Base Management</h1>
        <p class="subtitle" id="kb-subtitle">Edit building information and concierge Q&A content</p>
```

And add in the init function:

```javascript
        async function init() {
            // Update subtitle to show which user's KB
            const subtitle = document.getElementById('kb-subtitle');
            const userDisplay = currentUser === 'admin' ? 'Admin / Meridian Building' : 'Building B';
            subtitle.textContent = 'Editing: ' + userDisplay;
            
            await loadContent();
        }
```

- [ ] **Step 7: Commit KB page user integration**

```bash
git add frontend/index.html frontend/admin-knowledge-base.html
git commit -m "feat: integrate user selection with KB management page"
```

---

### Task 13: Update Setup Persona Script

**Files:**
- Modify: `scripts/setup_persona.py` - add CLI argument support

- [ ] **Step 1: Add argparse imports**

Add to imports section (after line 15):

```python
import argparse
```

- [ ] **Step 2: Modify imports to use USERS**

Replace line 20:

```python
from backend.config import TAVUS_API_KEY, TAVUS_REPLICA_ID, BACKEND_URL
```

With:

```python
from backend.config import TAVUS_API_KEY, BACKEND_URL, USERS
```

- [ ] **Step 3: Add CLI argument parser**

Replace the `async def main()` function (around line 312) with:

```python
async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Tavus persona for a user")
    parser.add_argument(
        "--user",
        type=str,
        choices=list(USERS.keys()),
        default="admin",
        help="User to create persona for (admin or buildingB)"
    )
    parser.add_argument(
        "--replica",
        type=str,
        help="Replica ID to use (overrides user config)"
    )
    args = parser.parse_args()
    
    if not TAVUS_API_KEY or TAVUS_API_KEY == "your_tavus_api_key_here":
        print("ERROR: Set TAVUS_API_KEY in your .env file before running this script.")
        sys.exit(1)
    
    user_config = USERS[args.user]
    replica_id = args.replica if args.replica else user_config["replica_id"]
    
    if not replica_id:
        print(f"ERROR: No replica_id configured for user {args.user}")
        print(f"Usage: python -m scripts.setup_persona --user {args.user} --replica <replica_id>")
        sys.exit(1)
    
    # Load KB files for this user to build context
    kb_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), user_config["kb_path"])
    building_info_path = os.path.join(kb_base_path, "building_info.txt")
    concierge_qa_path = os.path.join(kb_base_path, "concierge_qa.txt")
    
    if os.path.exists(building_info_path) and os.path.exists(concierge_qa_path):
        with open(building_info_path, "r") as f:
            building_info = f.read()
        with open(concierge_qa_path, "r") as f:
            concierge_qa = f.read()
        combined_context = f"{building_info}\n\n---\n\n{concierge_qa}"
    else:
        print(f"WARNING: KB files not found for {args.user}, using empty context")
        combined_context = ""
    
    # Update PERSONA_PAYLOAD with user-specific values
    PERSONA_PAYLOAD["default_replica_id"] = replica_id
    PERSONA_PAYLOAD["context"] = combined_context

    print(f"Creating persona for user: {args.user}")
    print(f"  Replica ID : {replica_id}")
    print(f"  Callback   : {BACKEND_URL}/webhooks/tavus")
    print(f"  Context    : {len(combined_context)} characters")

    result = await tavus_client.create_persona(PERSONA_PAYLOAD)

    persona_id = result.get("persona_id")
    print()
    print("Persona created successfully!")
    print(f"  persona_id: {persona_id}")
    print()
    print("Add this to your .env file:")
    if args.user == "admin":
        print(f"  ADMIN_PERSONA_ID={persona_id}")
    elif args.user == "buildingB":
        print(f"  BUILDINGB_PERSONA_ID={persona_id}")
    else:
        print(f"  {args.user.upper()}_PERSONA_ID={persona_id}")
```

- [ ] **Step 4: Verify script syntax**

```bash
python -m py_compile scripts/setup_persona.py
```

Expected: No errors

- [ ] **Step 5: Test script help output**

```bash
python -m scripts.setup_persona --help
```

Expected: Shows usage with --user and --replica options

- [ ] **Step 6: Commit setup persona changes**

```bash
git add scripts/setup_persona.py
git commit -m "feat: add CLI args to setup_persona for multi-user support"
```

---

### Task 14: Update Environment Variables

**Files:**
- Modify: `.env`

- [ ] **Step 1: Backup existing .env**

```bash
cp .env .env.backup
```

Expected: Backup created

- [ ] **Step 2: Update .env with new variables**

Modify `.env` to add/rename variables:

```bash
# Tavus API Configuration
TAVUS_API_KEY='45fd9f9333b046f391ce57408f685f93'

# Admin user persona
ADMIN_PERSONA_ID=p5c2370d05ad
ADMIN_REPLICA_ID=r1af76e94d00

# BuildingB user persona
BUILDINGB_PERSONA_ID=
BUILDINGB_REPLICA_ID=r90bbd427f71

# Legacy (kept for backward compatibility)
TAVUS_PERSONA_ID=p5c2370d05ad
TAVUS_REPLICA_ID=r1af76e94d00

BACKEND_URL=https://prepense-wrigglingly-corazon.ngrok-free.dev
JITSI_BASE_URL=https://meet.whitelakedigital.com

# Admin session configuration (unused but kept)
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

- [ ] **Step 3: Verify .env syntax**

```bash
python -c "from backend.config import USERS; print('Admin persona:', USERS['admin']['persona_id']); print('BuildingB replica:', USERS['buildingB']['replica_id'])"
```

Expected: Shows correct IDs

- [ ] **Step 4: Commit .env changes**

```bash
git add .env
git commit -m "config: update .env with multi-user persona configuration"
```

---

### Task 15: Create BuildingB Persona

**Files:**
- Run: `scripts/setup_persona.py`
- Modify: `.env` (add persona_id)

- [ ] **Step 1: Verify buildingB KB files exist**

```bash
ls -la knowledge-base/buildingB/
```

Expected: Shows building_info.txt and concierge_qa.txt

- [ ] **Step 2: Run setup_persona for buildingB**

```bash
python -m scripts.setup_persona --user buildingB --replica r90bbd427f71
```

Expected: 
- Creates persona on Tavus
- Prints persona_id
- Shows: "Add this to your .env file: BUILDINGB_PERSONA_ID=<id>"

- [ ] **Step 3: Copy persona_id to .env**

Copy the persona_id from the output and update `.env`:

```bash
BUILDINGB_PERSONA_ID=<paste_persona_id_here>
```

- [ ] **Step 4: Verify buildingB persona configured**

```bash
python -c "from backend.config import USERS; print('BuildingB persona:', USERS['buildingB']['persona_id'])"
```

Expected: Shows the new persona_id (not empty)

- [ ] **Step 5: Commit .env with buildingB persona_id**

```bash
git add .env
git commit -m "config: add buildingB persona_id to .env"
```

---

### Task 16: Manual Testing - Admin User

**Files:**
- Test: Frontend and backend integration

- [ ] **Step 1: Start the server**

```bash
./start.sh
```

Expected: Server starts on port 8001

- [ ] **Step 2: Open browser to http://localhost:8001**

Expected: Login screen visible with dropdown

- [ ] **Step 3: Select "Admin / Meridian Building" from dropdown**

Expected: Username field shows "admin"

- [ ] **Step 4: Enter password "meridian" and login**

Expected: Login successful, app screen visible

- [ ] **Step 5: Click "Start Conversation"**

Expected: 
- Admin persona conversation created
- Admin avatar appears (replica r1af76e94d00)
- No errors in browser console

- [ ] **Step 6: End conversation and navigate to KB page**

Expected: KB page loads with admin's files

- [ ] **Step 7: Verify admin KB content displayed**

Expected: Meridian building info visible

- [ ] **Step 8: Make a small edit and save**

Expected: Save successful message

- [ ] **Step 9: Click "Sync to Tavus"**

Expected: Sync successful message with character count

- [ ] **Step 10: Check server logs**

```bash
tail -50 server.log | grep "user"
```

Expected: Shows admin user in logs

---

### Task 17: Manual Testing - BuildingB User

**Files:**
- Test: BuildingB persona and KB isolation

- [ ] **Step 1: Logout from admin**

Expected: Returns to login screen

- [ ] **Step 2: Select "Building B" from dropdown**

Expected: Username field shows "buildingB"

- [ ] **Step 3: Enter password "meridian" and login**

Expected: Login successful

- [ ] **Step 4: Click "Start Conversation"**

Expected:
- BuildingB persona conversation created
- BuildingB avatar appears (different from admin - replica r90bbd427f71)
- No errors

- [ ] **Step 5: End conversation and navigate to KB page**

Expected: KB page loads showing "Editing: Building B"

- [ ] **Step 6: Verify buildingB KB content displayed**

Expected: Building B dummy content visible (Oak Street, rooftop terrace, etc.)

- [ ] **Step 7: Edit buildingB KB content**

Expected: Can edit and save successfully

- [ ] **Step 8: Click "Sync to Tavus"**

Expected: BuildingB persona synced

- [ ] **Step 9: Logout and login as admin again**

Expected: Admin KB unchanged (no Building B content)

- [ ] **Step 10: Verify isolation**

Expected: Admin and buildingB have completely separate KB files

---

### Task 18: Error Handling Testing

**Files:**
- Test: Error cases and edge conditions

- [ ] **Step 1: Test invalid username in API**

```bash
curl -X POST http://localhost:8001/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"username": "invalid"}'
```

Expected: 400 error: "Unknown user: invalid"

- [ ] **Step 2: Test missing persona_id (temporarily remove from .env)**

Edit .env, set `BUILDINGB_PERSONA_ID=`

```bash
curl -X POST http://localhost:8001/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"username": "buildingB"}'
```

Expected: 500 error mentioning persona not configured

Restore the persona_id in .env after test

- [ ] **Step 3: Test KB content with missing user**

```bash
curl http://localhost:8001/admin/knowledge-base/content?user=nonexistent
```

Expected: 400 error: "Unknown user"

- [ ] **Step 4: Test default to admin when no username provided**

```bash
curl -X POST http://localhost:8001/api/conversations \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected: Creates conversation with admin persona (no error)

- [ ] **Step 5: Verify all error cases handled gracefully**

Expected: No server crashes, appropriate error messages

---

### Task 19: Documentation Update

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md with multi-user info**

Add section after "Architecture" section:

```markdown
## Multi-User Support

The application supports multiple users with separate avatars and knowledge bases:

**Users:**
- `admin` - Meridian Building (default)
- `buildingB` - Building B

**Configuration:**
Users are defined in `backend/config.py` USERS dict. Each user has:
- Password (both use "meridian")
- Tavus persona_id (different avatar)
- Tavus replica_id (different appearance)
- KB directory path (separate content)

**Login:**
- Dropdown selection on login screen
- Username auto-filled based on selection
- SessionStorage persists user selection

**Conversation Flow:**
- Frontend sends `username` in POST /api/conversations
- Backend looks up user's persona_id
- Creates conversation with user-specific Tavus persona

**KB Management:**
- KB page detects user from URL param: `/admin/knowledge-base?user=buildingB`
- Load/save/sync operations target user-specific KB directory
- Complete isolation between users

**Creating New User Personas:**
```bash
# Create persona for a user
python -m scripts.setup_persona --user buildingB --replica <replica_id>

# Copy returned persona_id to .env
BUILDINGB_PERSONA_ID=<persona_id>
```

**Adding New Users:**
1. Add entry to USERS dict in `backend/config.py`
2. Create KB directory: `knowledge-base/<username>/`
3. Add persona/replica env vars to `.env`
4. Run `setup_persona.py` with new user
5. Add option to login dropdown in `frontend/index.html`
```

- [ ] **Step 2: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "docs: add multi-user support documentation"
```

---

### Task 20: Final Verification

**Files:**
- Verify: All components working together

- [ ] **Step 1: Stop and restart server**

```bash
./stop.sh
./start.sh
sleep 3
tail -20 server.log
```

Expected: Server starts cleanly, no errors

- [ ] **Step 2: Test complete flow for admin**

- Login as admin
- Start conversation
- Verify admin avatar
- Open KB page
- Verify admin content
- Logout

Expected: All steps work

- [ ] **Step 3: Test complete flow for buildingB**

- Login as buildingB
- Start conversation
- Verify buildingB avatar (different from admin)
- Open KB page
- Verify buildingB content
- Logout

Expected: All steps work

- [ ] **Step 4: Verify KB isolation**

- Login as buildingB
- Edit and save KB
- Logout
- Login as admin
- Open KB page
- Verify admin KB unchanged

Expected: Complete isolation

- [ ] **Step 5: Check all commits**

```bash
git log --oneline -20
```

Expected: Shows all commits from this implementation

- [ ] **Step 6: Create summary commit**

```bash
git add -A
git commit -m "feat: complete multi-user avatar system with buildingB

- Added user configuration in backend/config.py
- Modified conversation endpoint to support multi-user
- Updated all KB endpoints for user-specific paths
- Added user dropdown to login form
- Implemented sessionStorage for user persistence
- Modified setup_persona.py for CLI user selection
- Created buildingB KB with dummy content
- Migrated admin KB to subdirectory
- Added comprehensive error handling
- Updated documentation

Tested: Both users (admin/buildingB) with separate personas and KB isolation"
```

---

## Self-Review

**Spec Coverage:**
✓ Two users (admin/buildingB) - Tasks 3, 14, 15
✓ Same password - Task 3
✓ Separate personas - Tasks 13, 15
✓ Separate KB directories - Tasks 1, 2, 6-8
✓ Separate replicas - Task 3, 15
✓ Login dropdown - Task 9
✓ KB loads user-specific files - Tasks 6-8, 12
✓ No database changes - All tasks
✓ Error handling - Tasks 4-8, 18
✓ Migration steps - Tasks 1, 2, 14

**Placeholder Check:**
✓ No TODOs or TBDs
✓ All code blocks complete
✓ All commands have expected output
✓ File paths are exact

**Type Consistency:**
✓ USERS dict structure consistent across all files
✓ user/username used consistently
✓ persona_id, replica_id, kb_path fields match
✓ sessionStorage key "currentUser" used consistently
