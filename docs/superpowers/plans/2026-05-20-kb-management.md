# Knowledge Base Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build web-based admin interface for editing knowledge base files with session authentication, file save, and Tavus sync.

**Architecture:** Single HTML page (`/admin/knowledge-base`) with conditional rendering (login form OR editor). Session-based auth with in-memory store. Backend endpoints for auth, content CRUD, and Tavus sync.

**Tech Stack:** FastAPI, vanilla JavaScript, Pydantic, existing tavus_client

---

## File Structure

**Created:**
- `frontend/admin-knowledge-base.html` - Single-page admin interface with embedded CSS/JS

**Modified:**
- `backend/app.py` - Add session management, 6 endpoints, Pydantic models

---

## Task 1: Session Management Infrastructure

**Files:**
- Modify: `backend/app.py` (add after imports, before app creation)

- [ ] **Step 1: Add session management imports**

Add after existing imports in `backend/app.py`:

```python
import secrets
from datetime import datetime, timedelta
```

- [ ] **Step 2: Add session constants and store**

Add after logger definition, before app creation:

```python
# Admin session management
_admin_sessions: dict[str, dict] = {}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "meridian"
SESSION_DURATION_SECONDS = 7200  # 2 hours
```

- [ ] **Step 3: Add session helper functions**

Add after session constants:

```python
def create_session(username: str) -> str:
    """Create a new admin session and return session ID."""
    session_id = secrets.token_urlsafe(32)
    _admin_sessions[session_id] = {
        "username": username,
        "expires_at": datetime.utcnow() + timedelta(seconds=SESSION_DURATION_SECONDS),
    }
    logger.info(f"Session created for user: {username}")
    return session_id


def validate_session(session_id: str) -> bool:
    """Check if session ID is valid and not expired."""
    if not session_id or session_id not in _admin_sessions:
        return False
    session = _admin_sessions[session_id]
    if datetime.utcnow() > session["expires_at"]:
        del _admin_sessions[session_id]
        logger.info(f"Session expired and removed: {session_id[:8]}...")
        return False
    return True


def destroy_session(session_id: str) -> None:
    """Remove session from store."""
    _admin_sessions.pop(session_id, None)
    logger.info(f"Session destroyed: {session_id[:8]}...")
```

- [ ] **Step 4: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add backend/app.py
git commit -m "feat: add session management infrastructure for admin auth

- In-memory session store with 2-hour expiration
- Helper functions: create_session, validate_session, destroy_session
- Hardcoded credentials: admin/meridian

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Authentication Endpoint

**Files:**
- Modify: `backend/app.py` (add Pydantic model and endpoint)

- [ ] **Step 1: Add Pydantic model for auth request**

Add after other Pydantic models (after `EscalateToHumanRequest`):

```python
class AdminAuthRequest(BaseModel):
    username: str
    password: str
```

- [ ] **Step 2: Add authentication endpoint**

Add before the Tavus webhook section:

```python
# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------
@app.post("/admin/auth")
async def admin_auth(body: AdminAuthRequest, response: Response):
    """Authenticate admin user and create session."""
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        logger.warning(f"Failed login attempt for user: {body.username}")
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid username or password"},
        )
    
    session_id = create_session(body.username)
    response.set_cookie(
        key="admin_session",
        value=session_id,
        httponly=True,
        max_age=SESSION_DURATION_SECONDS,
        path="/admin",
    )
    
    logger.info(f"Successful login for user: {body.username}")
    return {"status": "ok"}
```

- [ ] **Step 3: Add Response import**

Add `Response` to FastAPI imports at top of file:

```python
from fastapi import FastAPI, Request, Response
```

- [ ] **Step 4: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add backend/app.py
git commit -m "feat: add admin authentication endpoint

- POST /admin/auth validates credentials
- Sets httpOnly session cookie on success
- Logs all login attempts

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Content Retrieval Endpoint

**Files:**
- Modify: `backend/app.py` (add protected endpoint)

- [ ] **Step 1: Add content retrieval endpoint**

Add after `/admin/auth` endpoint:

```python
@app.get("/admin/knowledge-base/content")
async def get_kb_content(request: Request):
    """Get current knowledge base file contents (protected)."""
    session_id = request.cookies.get("admin_session")
    if not validate_session(session_id):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
        )
    
    try:
        building_info_path = FRONTEND_DIR.parent / "knowledge-base" / "building_info.txt"
        concierge_qa_path = FRONTEND_DIR.parent / "knowledge-base" / "concierge_qa.txt"
        
        building_info = building_info_path.read_text()
        concierge_qa = concierge_qa_path.read_text()
        
        logger.info(f"Knowledge base content retrieved by session: {session_id[:8]}...")
        return {
            "building_info": building_info,
            "concierge_qa": concierge_qa,
        }
    except FileNotFoundError as e:
        logger.error(f"Knowledge base file not found: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read knowledge base files"},
        )
    except Exception as e:
        logger.error(f"Error reading knowledge base: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to read knowledge base files: {str(e)}"},
        )
```

- [ ] **Step 2: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: add knowledge base content retrieval endpoint

- GET /admin/knowledge-base/content returns both KB files
- Session validation protects endpoint
- Error handling for missing files

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Save Endpoint

**Files:**
- Modify: `backend/app.py` (add Pydantic model and save endpoint)

- [ ] **Step 1: Add Pydantic model for save request**

Add after `AdminAuthRequest`:

```python
class KnowledgeBaseSaveRequest(BaseModel):
    building_info: str
    concierge_qa: str
```

- [ ] **Step 2: Add save endpoint**

Add after `/admin/knowledge-base/content` endpoint:

```python
@app.post("/admin/knowledge-base/save")
async def save_kb_content(body: KnowledgeBaseSaveRequest, request: Request):
    """Save knowledge base file contents (protected)."""
    session_id = request.cookies.get("admin_session")
    if not validate_session(session_id):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
        )
    
    # Validate non-empty
    if not body.building_info or not body.building_info.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Content cannot be empty: building_info"},
        )
    if not body.concierge_qa or not body.concierge_qa.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Content cannot be empty: concierge_qa"},
        )
    
    try:
        kb_dir = FRONTEND_DIR.parent / "knowledge-base"
        building_info_path = kb_dir / "building_info.txt"
        concierge_qa_path = kb_dir / "concierge_qa.txt"
        
        building_info_path.write_text(body.building_info)
        concierge_qa_path.write_text(body.concierge_qa)
        
        username = _admin_sessions.get(session_id, {}).get("username", "unknown")
        logger.info(f"Knowledge base files saved by user: {username}")
        return {
            "status": "ok",
            "message": "Files saved successfully",
        }
    except PermissionError:
        logger.error("Permission denied writing to knowledge-base/")
        return JSONResponse(
            status_code=500,
            content={"error": "Permission denied writing to knowledge-base/"},
        )
    except Exception as e:
        logger.error(f"Error saving knowledge base: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save files: {str(e)}"},
        )
```

- [ ] **Step 3: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat: add knowledge base save endpoint

- POST /admin/knowledge-base/save writes both KB files
- Validates non-empty content
- Session-protected with error handling

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Sync Endpoint

**Files:**
- Modify: `backend/app.py` (add sync endpoint)

- [ ] **Step 1: Add sync endpoint**

Add after `/admin/knowledge-base/save` endpoint:

```python
@app.post("/admin/knowledge-base/sync")
async def sync_kb_to_tavus(request: Request):
    """Sync knowledge base content to Tavus persona context (protected)."""
    session_id = request.cookies.get("admin_session")
    if not validate_session(session_id):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
        )
    
    if not TAVUS_PERSONA_ID or TAVUS_PERSONA_ID == "your_persona_id_here":
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid TAVUS_PERSONA_ID configuration"},
        )
    
    try:
        kb_dir = FRONTEND_DIR.parent / "knowledge-base"
        building_info_path = kb_dir / "building_info.txt"
        concierge_qa_path = kb_dir / "concierge_qa.txt"
        
        building_info = building_info_path.read_text()
        concierge_qa = concierge_qa_path.read_text()
        
        # Combine content (same logic as update_persona_context.py)
        combined = (
            building_info.strip()
            + "\n\n"
            + "=" * 40
            + "\n"
            + concierge_qa.strip()
        )
        
        operations = [
            {"op": "replace", "path": "/context", "value": combined},
        ]
        
        result = await tavus_client.patch_persona(TAVUS_PERSONA_ID, operations)
        
        username = _admin_sessions.get(session_id, {}).get("username", "unknown")
        logger.info(f"Tavus persona synced by user: {username} ({len(combined)} chars)")
        
        return {
            "status": "ok",
            "message": "Tavus persona updated",
            "chars": len(combined),
        }
    except FileNotFoundError as e:
        logger.error(f"Knowledge base file not found during sync: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to read knowledge base files"},
        )
    except Exception as e:
        logger.error(f"Error syncing to Tavus: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Tavus API error: {str(e)}"},
        )
```

- [ ] **Step 2: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: add Tavus sync endpoint

- POST /admin/knowledge-base/sync updates persona context
- Reads current files, combines content, calls Tavus API
- Returns character count on success

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Logout Endpoint

**Files:**
- Modify: `backend/app.py` (add logout endpoint)

- [ ] **Step 1: Add logout endpoint**

Add after `/admin/knowledge-base/sync` endpoint:

```python
@app.post("/admin/logout")
async def admin_logout(request: Request, response: Response):
    """Destroy admin session and clear cookie (protected)."""
    session_id = request.cookies.get("admin_session")
    if not validate_session(session_id):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
        )
    
    destroy_session(session_id)
    response.delete_cookie(key="admin_session", path="/admin")
    
    return {"status": "ok"}
```

- [ ] **Step 2: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: add admin logout endpoint

- POST /admin/logout destroys session
- Clears httpOnly cookie
- Session-protected

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Serve Admin Page Endpoint

**Files:**
- Modify: `backend/app.py` (add route to serve HTML)

- [ ] **Step 1: Add admin page route**

Add after `/conversations` route (around line 75):

```python
@app.get("/admin/knowledge-base", response_class=HTMLResponse)
async def admin_kb_page():
    """Serve admin knowledge base management page."""
    try:
        with open(FRONTEND_DIR / "admin-knowledge-base.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("admin-knowledge-base.html not found")
        return HTMLResponse(content="<h1>Admin Page Not Found</h1>", status_code=404)
```

- [ ] **Step 2: Verify syntax**

Run: `venv/bin/python -m py_compile backend/app.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: add admin page route

- GET /admin/knowledge-base serves HTML page
- No auth check (client-side handles session)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Create Admin HTML Page - Structure

**Files:**
- Create: `frontend/admin-knowledge-base.html`

- [ ] **Step 1: Create HTML structure**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Knowledge Base Management</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            max-width: 1200px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        /* Message box */
        .message {
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
            align-items: center;
            justify-content: space-between;
        }
        
        .message.show {
            display: flex;
        }
        
        .message.error {
            background: #fee;
            color: #c33;
            border: 1px solid #fcc;
        }
        
        .message.success {
            background: #efe;
            color: #3a3;
            border: 1px solid #cfc;
        }
        
        .message-close {
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: inherit;
            padding: 0 5px;
        }
        
        /* Login form */
        #login-view {
            display: none;
        }
        
        #login-view.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        /* Editor view */
        #editor-view {
            display: none;
        }
        
        #editor-view.active {
            display: block;
        }
        
        .header-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .editor-section {
            margin-bottom: 30px;
        }
        
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .editor-label {
            font-weight: 600;
            color: #333;
            font-size: 16px;
        }
        
        .char-count {
            color: #666;
            font-size: 13px;
        }
        
        textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-family: "Courier New", monospace;
            font-size: 13px;
            resize: vertical;
            min-height: 250px;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        /* Buttons */
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            background: #5568d3;
        }
        
        .btn-success {
            background: #48bb78;
            color: white;
        }
        
        .btn-success:hover:not(:disabled) {
            background: #38a169;
        }
        
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
        }
        
        .btn-secondary:hover:not(:disabled) {
            background: #cbd5e0;
        }
        
        .btn-group {
            display: flex;
            gap: 12px;
        }
        
        .loading {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Knowledge Base Management</h1>
        <p class="subtitle">Edit building information and concierge Q&A content</p>
        
        <!-- Message box -->
        <div id="message" class="message">
            <span id="message-text"></span>
            <button class="message-close" onclick="hideMessage()">&times;</button>
        </div>
        
        <!-- Login View -->
        <div id="login-view">
            <form id="login-form" onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>
                <button type="submit" class="btn btn-primary" id="login-btn">Login</button>
            </form>
        </div>
        
        <!-- Editor View -->
        <div id="editor-view">
            <div class="header-actions">
                <div class="btn-group">
                    <button class="btn btn-success" onclick="handleSave()" id="save-btn">Save Files</button>
                    <button class="btn btn-primary" onclick="handleSync()" id="sync-btn">Sync to Tavus</button>
                </div>
                <button class="btn btn-secondary" onclick="handleLogout()">Logout</button>
            </div>
            
            <div class="editor-section">
                <div class="editor-header">
                    <span class="editor-label">Building Information</span>
                    <span class="char-count" id="building-char-count">0 characters</span>
                </div>
                <textarea id="building-info" oninput="updateCharCount('building')"></textarea>
            </div>
            
            <div class="editor-section">
                <div class="editor-header">
                    <span class="editor-label">Concierge Q&A</span>
                    <span class="char-count" id="qa-char-count">0 characters</span>
                </div>
                <textarea id="concierge-qa" oninput="updateCharCount('qa')"></textarea>
            </div>
        </div>
    </div>

    <script>
        // JavaScript will be added in next task
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify file created**

Run: `ls -la frontend/admin-knowledge-base.html`
Expected: File exists

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-knowledge-base.html
git commit -m "feat: add admin page HTML structure and styles

- Login form and editor views with conditional rendering
- Styled message box for feedback
- Responsive layout with gradient background

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Add JavaScript - State Management and UI

**Files:**
- Modify: `frontend/admin-knowledge-base.html` (add JavaScript)

- [ ] **Step 1: Replace empty script tag with state and UI functions**

Replace `<script>` section with:

```javascript
    <script>
        // State
        let isAuthenticated = false;
        let messageTimeout = null;
        
        // Initialize on page load
        window.addEventListener('DOMContentLoaded', init);
        
        async function init() {
            // Try to fetch content (checks session validity)
            await checkSession();
        }
        
        async function checkSession() {
            try {
                const response = await fetch('/admin/knowledge-base/content');
                if (response.ok) {
                    const data = await response.json();
                    loadEditor(data);
                } else {
                    showLogin();
                }
            } catch (error) {
                console.error('Session check failed:', error);
                showLogin();
            }
        }
        
        function showLogin() {
            isAuthenticated = false;
            document.getElementById('login-view').classList.add('active');
            document.getElementById('editor-view').classList.remove('active');
        }
        
        function showEditor() {
            isAuthenticated = true;
            document.getElementById('login-view').classList.remove('active');
            document.getElementById('editor-view').classList.add('active');
        }
        
        function loadEditor(data) {
            const buildingTextarea = document.getElementById('building-info');
            const qaTextarea = document.getElementById('concierge-qa');
            
            buildingTextarea.value = data.building_info;
            qaTextarea.value = data.concierge_qa;
            
            updateCharCount('building');
            updateCharCount('qa');
            
            showEditor();
        }
        
        function updateCharCount(type) {
            if (type === 'building') {
                const textarea = document.getElementById('building-info');
                const count = document.getElementById('building-char-count');
                count.textContent = `${textarea.value.length} characters`;
            } else if (type === 'qa') {
                const textarea = document.getElementById('concierge-qa');
                const count = document.getElementById('qa-char-count');
                count.textContent = `${textarea.value.length} characters`;
            }
        }
        
        function showMessage(text, type = 'success') {
            const messageBox = document.getElementById('message');
            const messageText = document.getElementById('message-text');
            
            messageText.textContent = text;
            messageBox.className = `message show ${type}`;
            
            // Auto-dismiss after 5 seconds
            clearTimeout(messageTimeout);
            messageTimeout = setTimeout(hideMessage, 5000);
        }
        
        function hideMessage() {
            const messageBox = document.getElementById('message');
            messageBox.classList.remove('show');
            clearTimeout(messageTimeout);
        }
        
        function setButtonLoading(buttonId, loading) {
            const button = document.getElementById(buttonId);
            if (loading) {
                button.disabled = true;
                const originalText = button.textContent;
                button.dataset.originalText = originalText;
                // Create loading spinner element
                const spinner = document.createElement('span');
                spinner.className = 'loading';
                button.textContent = '';
                button.appendChild(spinner);
                button.appendChild(document.createTextNode(originalText));
            } else {
                button.disabled = false;
                button.textContent = button.dataset.originalText || button.textContent;
            }
        }
    </script>
```

- [ ] **Step 2: Verify syntax by opening in browser**

Run: `./start.sh` (if not running)
Open: `http://localhost:8001/admin/knowledge-base`
Expected: Login form displays

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-knowledge-base.html
git commit -m "feat: add JavaScript state management and UI helpers

- Session check on page load
- View switching (login/editor)
- Character count updates
- Message box with auto-dismiss
- Button loading states (safe DOM methods)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Add JavaScript - Authentication Handlers

**Files:**
- Modify: `frontend/admin-knowledge-base.html` (add auth functions)

- [ ] **Step 1: Add authentication handlers before closing script tag**

Add before `</script>`:

```javascript
        
        // Authentication handlers
        async function handleLogin(event) {
            event.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            setButtonLoading('login-btn', true);
            hideMessage();
            
            try {
                const response = await fetch('/admin/auth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password }),
                });
                
                if (response.ok) {
                    // Fetch content and show editor
                    await checkSession();
                    showMessage('Login successful', 'success');
                } else {
                    const error = await response.json();
                    showMessage(error.error || 'Login failed', 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                showMessage('Login failed: Network error', 'error');
            } finally {
                setButtonLoading('login-btn', false);
            }
        }
        
        async function handleLogout() {
            try {
                await fetch('/admin/logout', { method: 'POST' });
                showLogin();
                showMessage('Logged out successfully', 'success');
                
                // Clear form
                document.getElementById('username').value = '';
                document.getElementById('password').value = '';
            } catch (error) {
                console.error('Logout error:', error);
                showMessage('Logout failed', 'error');
            }
        }
```

- [ ] **Step 2: Test login flow**

Run: Open `http://localhost:8001/admin/knowledge-base`
Actions:
1. Enter username: `admin`, password: `meridian`
2. Click "Login"
Expected: Login successful, editor displays with KB content

- [ ] **Step 3: Test logout**

Actions: Click "Logout"
Expected: Returns to login form, success message

- [ ] **Step 4: Test invalid credentials**

Actions: Enter wrong password, click "Login"
Expected: Error message "Invalid username or password"

- [ ] **Step 5: Commit**

```bash
git add frontend/admin-knowledge-base.html
git commit -m "feat: add authentication handlers

- handleLogin validates credentials and loads editor
- handleLogout clears session and returns to login
- Error handling with user feedback

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Add JavaScript - Save Handler

**Files:**
- Modify: `frontend/admin-knowledge-base.html` (add save function)

- [ ] **Step 1: Add save handler before closing script tag**

Add before `</script>`:

```javascript
        
        // Save handler
        async function handleSave() {
            const buildingInfo = document.getElementById('building-info').value;
            const conciergeQa = document.getElementById('concierge-qa').value;
            
            if (!buildingInfo.trim()) {
                showMessage('Building information cannot be empty', 'error');
                return;
            }
            
            if (!conciergeQa.trim()) {
                showMessage('Concierge Q&A cannot be empty', 'error');
                return;
            }
            
            setButtonLoading('save-btn', true);
            hideMessage();
            
            try {
                const response = await fetch('/admin/knowledge-base/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        building_info: buildingInfo,
                        concierge_qa: conciergeQa,
                    }),
                });
                
                if (response.ok) {
                    const data = await response.json();
                    showMessage(data.message || 'Files saved successfully', 'success');
                } else if (response.status === 401) {
                    showMessage('Session expired, please login again', 'error');
                    setTimeout(showLogin, 2000);
                } else {
                    const error = await response.json();
                    showMessage(error.error || 'Save failed', 'error');
                }
            } catch (error) {
                console.error('Save error:', error);
                showMessage('Save failed: Network error', 'error');
            } finally {
                setButtonLoading('save-btn', false);
            }
        }
```

- [ ] **Step 2: Test save with valid content**

Actions:
1. Login
2. Modify text in either textarea
3. Click "Save Files"
Expected: Success message "Files saved successfully"

- [ ] **Step 3: Verify files updated on disk**

Run: `head -5 knowledge-base/building_info.txt`
Expected: Shows modified content (if you edited that file)

- [ ] **Step 4: Test save with empty content**

Actions:
1. Clear all text from building_info textarea
2. Click "Save Files"
Expected: Error message "Building information cannot be empty"

- [ ] **Step 5: Commit**

```bash
git add frontend/admin-knowledge-base.html
git commit -m "feat: add save handler

- Validates non-empty content before save
- Writes both KB files via API
- Handles session expiration
- User feedback for all outcomes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Add JavaScript - Sync Handler

**Files:**
- Modify: `frontend/admin-knowledge-base.html` (add sync function)

- [ ] **Step 1: Add sync handler before closing script tag**

Add before `</script>`:

```javascript
        
        // Sync handler
        async function handleSync() {
            setButtonLoading('sync-btn', true);
            hideMessage();
            
            try {
                const response = await fetch('/admin/knowledge-base/sync', {
                    method: 'POST',
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const charInfo = data.chars ? ` (${data.chars} characters)` : '';
                    showMessage(data.message + charInfo || 'Tavus persona updated', 'success');
                } else if (response.status === 401) {
                    showMessage('Session expired, please login again', 'error');
                    setTimeout(showLogin, 2000);
                } else {
                    const error = await response.json();
                    showMessage(error.error || 'Sync failed', 'error');
                }
            } catch (error) {
                console.error('Sync error:', error);
                showMessage('Sync failed: Network error', 'error');
            } finally {
                setButtonLoading('sync-btn', false);
            }
        }
```

- [ ] **Step 2: Test sync**

Actions:
1. Login
2. Click "Sync to Tavus"
Expected: Success message "Tavus persona updated (XXXX characters)"

- [ ] **Step 3: Verify Tavus API called**

Check logs: `tail -20 server.log`
Expected: Line like "Tavus persona synced by user: admin (XXXX chars)"

- [ ] **Step 4: Test sync after save**

Actions:
1. Modify content
2. Click "Save Files"
3. Click "Sync to Tavus"
Expected: Both operations succeed, sync uses updated content

- [ ] **Step 5: Commit**

```bash
git add frontend/admin-knowledge-base.html
git commit -m "feat: add Tavus sync handler

- Syncs current KB files to Tavus persona context
- Displays character count on success
- Handles session expiration
- Uses files from disk (not textarea state)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 13: Manual Testing - Authentication Flow

**Files:**
- None (testing only)

- [ ] **Step 1: Test correct credentials**

Actions:
1. Stop server: `./stop.sh`
2. Start server: `./start.sh`
3. Open: `http://localhost:8001/admin/knowledge-base`
4. Enter username: `admin`, password: `meridian`
5. Click "Login"
Expected: Editor displays with current KB content

- [ ] **Step 2: Test incorrect credentials**

Actions:
1. Logout
2. Enter username: `wrong`, password: `wrong`
3. Click "Login"
Expected: Error message "Invalid username or password", stays on login

- [ ] **Step 3: Test session persistence**

Actions:
1. Login successfully
2. Refresh page (F5)
Expected: Still shows editor (session persists)

- [ ] **Step 4: Test session expiration (simulated)**

Note: Full 2-hour expiration not practical to test manually.
Verified: Code checks expiration in `validate_session()`.

- [ ] **Step 5: Document test results**

Create note: All authentication tests pass ✓

---

## Task 14: Manual Testing - Editor Functionality

**Files:**
- None (testing only)

- [ ] **Step 1: Test text areas populated**

Actions: After login, check both textareas
Expected: building_info.txt content in first textarea, concierge_qa.txt in second

- [ ] **Step 2: Test character counts**

Actions: Modify text in building_info textarea
Expected: Character count updates in real-time as you type

- [ ] **Step 3: Test content editable**

Actions: Edit both textareas
Expected: Both allow text editing

- [ ] **Step 4: Test character counts for both fields**

Actions: Type in concierge_qa textarea
Expected: QA character count updates

- [ ] **Step 5: Document test results**

Create note: All editor functionality tests pass ✓

---

## Task 15: Manual Testing - Save Operation

**Files:**
- None (testing only)

- [ ] **Step 1: Test save with modified content**

Actions:
1. Login
2. Change text in building_info: add "TEST EDIT" at top
3. Click "Save Files"
Expected: Success message "Files saved successfully"

- [ ] **Step 2: Verify file saved to disk**

Run: `head -3 knowledge-base/building_info.txt`
Expected: Shows "TEST EDIT" at top

- [ ] **Step 3: Test save persists after refresh**

Actions:
1. Refresh page
2. Check building_info textarea
Expected: "TEST EDIT" still present

- [ ] **Step 4: Test empty content rejection**

Actions:
1. Clear all text from building_info textarea
2. Click "Save Files"
Expected: Error message "Building information cannot be empty"

- [ ] **Step 5: Restore original content**

Actions:
1. Remove "TEST EDIT" text
2. Click "Save Files"
Expected: Files restored to original state

---

## Task 16: Manual Testing - Sync Operation

**Files:**
- None (testing only)

- [ ] **Step 1: Test sync with current content**

Actions:
1. Login
2. Click "Sync to Tavus"
Expected: Success message "Tavus persona updated (XXXX characters)"

- [ ] **Step 2: Verify character count reasonable**

Check message character count
Expected: ~12000-13000 characters (building_info + concierge_qa combined)

- [ ] **Step 3: Check logs for sync confirmation**

Run: `tail -30 server.log | grep "Tavus persona synced"`
Expected: Log line with username and character count

- [ ] **Step 4: Test sync after save**

Actions:
1. Modify content: add "SYNC TEST" to building_info
2. Click "Save Files"
3. Click "Sync to Tavus"
Expected: Both succeed, logs show sync with new content

- [ ] **Step 5: Restore and sync**

Actions:
1. Remove "SYNC TEST"
2. Save
3. Sync to Tavus
Expected: Tavus context restored to original

---

## Task 17: Manual Testing - Error Scenarios

**Files:**
- None (testing only)

- [ ] **Step 1: Test session expired (protected endpoint)**

Note: Simulated by clearing cookie in browser DevTools
Actions:
1. Login
2. Open browser DevTools → Application → Cookies
3. Delete `admin_session` cookie
4. Click "Save Files"
Expected: Error message "Session expired, please login again", returns to login

- [ ] **Step 2: Test invalid Tavus API (simulated)**

Note: Actual test requires breaking TAVUS_PERSONA_ID or network
Verified: Code catches exceptions and returns error message

- [ ] **Step 3: Test message auto-dismiss**

Actions:
1. Login
2. Click "Save Files" (triggers success message)
3. Wait 5 seconds
Expected: Message automatically disappears

- [ ] **Step 4: Test message manual dismiss**

Actions:
1. Click "Save Files"
2. Click X button on message
Expected: Message immediately disappears

- [ ] **Step 5: Document test results**

Create note: All error handling tests pass ✓

---

## Task 18: Manual Testing - Security

**Files:**
- None (testing only)

- [ ] **Step 1: Verify endpoints require authentication**

Actions:
1. Logout
2. Open browser DevTools → Console
3. Run: `fetch('/admin/knowledge-base/content').then(r => r.json()).then(console.log)`
Expected: Returns `{error: "Authentication required"}` with 401 status

- [ ] **Step 2: Verify session cookie is httpOnly**

Actions:
1. Login
2. DevTools → Application → Cookies
3. Check `admin_session` cookie properties
Expected: HttpOnly flag is checked

- [ ] **Step 3: Verify logout clears session**

Actions:
1. Login
2. Note session cookie value in DevTools
3. Logout
4. Check cookies again
Expected: `admin_session` cookie removed

- [ ] **Step 4: Verify cookie path restriction**

Check cookie: Path should be `/admin`
Expected: Cookie only sent to `/admin/*` routes

- [ ] **Step 5: Document test results**

Create note: All security tests pass ✓

---

## Task 19: Browser Compatibility Testing

**Files:**
- None (testing only)

- [ ] **Step 1: Test in Chrome**

Actions: Open `http://localhost:8001/admin/knowledge-base` in Chrome
Run through: Login, edit, save, sync, logout
Expected: All features work correctly

- [ ] **Step 2: Test in Firefox**

Actions: Same tests in Firefox
Expected: All features work correctly

- [ ] **Step 3: Test in Safari (if available)**

Actions: Same tests in Safari
Expected: All features work correctly

- [ ] **Step 4: Document browser test results**

Note browsers tested and any issues found

- [ ] **Step 5: Skip mobile testing**

Note: Mobile responsive not required per spec (admin tool)

---

## Task 20: Final Verification and Cleanup

**Files:**
- None (verification only)

- [ ] **Step 1: Verify all endpoints respond correctly**

Run server and check each endpoint:
- GET `/admin/knowledge-base` → HTML page
- POST `/admin/auth` → session created
- GET `/admin/knowledge-base/content` → KB files returned
- POST `/admin/knowledge-base/save` → files written
- POST `/admin/knowledge-base/sync` → Tavus updated
- POST `/admin/logout` → session destroyed

Expected: All work as specified

- [ ] **Step 2: Check git status**

Run: `git status`
Expected: No uncommitted changes (all work committed)

- [ ] **Step 3: Review commit history**

Run: `git log --oneline -20`
Expected: ~20 commits for this feature, all with clear messages

- [ ] **Step 4: Verify server starts without errors**

Actions:
1. Stop: `./stop.sh`
2. Start: `./start.sh`
3. Check: `tail -20 server.log`
Expected: No errors, server running on port 8001

- [ ] **Step 5: Final smoke test**

Actions: Complete workflow: login → edit → save → sync → logout
Expected: All operations succeed, no errors in logs

---

## Self-Review

**Spec Coverage:**
- ✓ View current KB content (Task 3, 8)
- ✓ Edit content inline (Task 8)
- ✓ Save changes to disk (Task 4, 11)
- ✓ Trigger Tavus sync (Task 5, 12)
- ✓ Username/password auth (Task 2, 10)
- ✓ Session-based with 2-hour expiration (Task 1)
- ✓ Success/error feedback (Task 8, 9)

**Placeholder Scan:**
- ✓ No TBD/TODO markers
- ✓ All code blocks complete
- ✓ All test steps have expected outcomes
- ✓ No "implement later" or "similar to Task N"

**Type Consistency:**
- ✓ Pydantic models match endpoint handlers
- ✓ JavaScript fetch payloads match backend expectations
- ✓ Session structure consistent across all functions
- ✓ File paths consistent (knowledge-base/*.txt)

All requirements covered. No placeholders. Types consistent.
