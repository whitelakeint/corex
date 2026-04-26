# Tavus AI Avatar + Jitsi Meet Integration Guide

## Concept

```
User <--video--> Tavus AI Avatar (persona)
                      |
            [Out-of-scope detected]
                      |
                      v
         Jitsi Meet room created
                      |
         User redirected to Jitsi call
                      |
         Human agent joins the same room
```

When the Tavus AI avatar cannot answer a user's question (out-of-scope), the system:
1. Detects the out-of-scope condition
2. Creates a Jitsi Meet room
3. Redirects the user to the Jitsi video call
4. Notifies a human agent to join the same room

---

## Integration Steps

### Step 1: Configure Tavus Conversation with a Webhook

When creating a Tavus conversation via their API, set up a **conversation callback/webhook** to receive events. Tavus sends real-time events including conversation transcripts and custom tool calls.

```bash
# Tavus API - Create a conversation with webhook
curl -X POST https://tavusapi.com/v2/conversations \
  -H "x-api-key: YOUR_TAVUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "YOUR_PERSONA_ID",
    "callback_url": "https://your-backend.com/api/tavus/webhook",
    "conversational_context": "You are a helpful assistant for Whitelake Digital. If the user asks something outside your knowledge or scope, call the escalate_to_human tool.",
    "custom_tools": [
      {
        "type": "function",
        "function": {
          "name": "escalate_to_human",
          "description": "Call this when the user asks a question you cannot answer, or requests to speak with a real person",
          "parameters": {
            "type": "object",
            "properties": {
              "reason": {
                "type": "string",
                "description": "Brief reason why escalation is needed"
              },
              "user_question": {
                "type": "string",
                "description": "The question the user asked that triggered escalation"
              }
            },
            "required": ["reason"]
          }
        }
      }
    ]
  }'
```

The key here is the **custom tool** `escalate_to_human`. The Tavus persona's LLM will call this tool when it detects an out-of-scope question based on the conversational context you provide.

---

### Step 2: Backend - Handle the Escalation Webhook

Your backend receives the tool call from Tavus, creates a Jitsi room, and returns the meeting URL.

```python
# Python (FastAPI example)
from fastapi import FastAPI, Request
import uuid
import httpx
import time

app = FastAPI()

JITSI_BASE_URL = "https://172.83.83.168"  # Your Jitsi server
AGENT_NOTIFICATION_URL = "https://your-backend.com/api/notify-agent"  # Internal

@app.post("/api/tavus/webhook")
async def tavus_webhook(request: Request):
    payload = await request.json()

    event_type = payload.get("event_type")

    # Handle tool call event
    if event_type == "tool_call":
        tool_name = payload.get("tool_name") or payload.get("function", {}).get("name")

        if tool_name == "escalate_to_human":
            arguments = payload.get("arguments", {})
            reason = arguments.get("reason", "User needs human assistance")

            # Create a unique Jitsi room
            room_id = f"support-{uuid.uuid4().hex[:8]}"
            meeting_url = f"{JITSI_BASE_URL}/{room_id}"

            # Notify human agent (see Step 4)
            await notify_agent(
                room_id=room_id,
                meeting_url=meeting_url,
                reason=reason,
                user_question=arguments.get("user_question", ""),
                conversation_id=payload.get("conversation_id")
            )

            # Return the meeting URL to Tavus (the persona can tell the user)
            return {
                "tool_response": {
                    "meeting_url": meeting_url,
                    "message": f"I've connected you with a human agent. Please join: {meeting_url}"
                }
            }

    return {"status": "ok"}


async def notify_agent(room_id, meeting_url, reason, user_question, conversation_id):
    """Notify available human agent via your preferred channel"""
    notification = {
        "room_id": room_id,
        "meeting_url": meeting_url,
        "reason": reason,
        "user_question": user_question,
        "conversation_id": conversation_id,
        "timestamp": time.time()
    }

    # Option A: Send to agent dashboard via WebSocket
    # Option B: Send Slack/Teams notification
    # Option C: Push notification to agent app
    # Option D: Add to agent queue in your database

    async with httpx.AsyncClient() as client:
        await client.post(AGENT_NOTIFICATION_URL, json=notification)
```

```javascript
// Node.js (Express example)
const express = require('express');
const crypto = require('crypto');
const app = express();

const JITSI_BASE_URL = 'https://172.83.83.168';

app.post('/api/tavus/webhook', express.json(), async (req, res) => {
    const { event_type, tool_name, arguments: args, conversation_id } = req.body;

    if (event_type === 'tool_call' && tool_name === 'escalate_to_human') {
        const roomId = `support-${crypto.randomBytes(4).toString('hex')}`;
        const meetingUrl = `${JITSI_BASE_URL}/${roomId}`;

        // Notify human agent
        await notifyAgent({
            roomId,
            meetingUrl,
            reason: args?.reason || 'User needs help',
            userQuestion: args?.user_question || '',
            conversationId: conversation_id
        });

        return res.json({
            tool_response: {
                meeting_url: meetingUrl,
                message: `I've connected you with a human agent. Please join: ${meetingUrl}`
            }
        });
    }

    res.json({ status: 'ok' });
});
```

---

### Step 3: Frontend - Redirect User to Jitsi

When the Tavus persona responds with the meeting URL, your frontend should detect it and redirect or embed the Jitsi call.

**Option A: Redirect to Jitsi (simplest)**
```javascript
// In your Tavus conversation handler
tavusConversation.on('message', (message) => {
    // Check if the AI response contains a meeting URL
    const meetingUrlMatch = message.text.match(/https:\/\/172\.83\.83\.168\/[\w-]+/);
    if (meetingUrlMatch) {
        const meetingUrl = meetingUrlMatch[0];

        // End Tavus conversation
        tavusConversation.end();

        // Redirect to Jitsi
        window.location.href = meetingUrl;
    }
});
```

**Option B: Embed Jitsi in-page using IFrame API (better UX)**
```html
<div id="tavus-container">
    <!-- Tavus avatar video here -->
</div>
<div id="jitsi-container" style="display:none; width:100%; height:600px;">
    <!-- Jitsi will load here -->
</div>

<script src="https://172.83.83.168/external_api.js"></script>
<script>
function switchToJitsi(roomName) {
    // Hide Tavus
    document.getElementById('tavus-container').style.display = 'none';
    document.getElementById('jitsi-container').style.display = 'block';

    // Load Jitsi Meet
    const api = new JitsiMeetExternalAPI('172.83.83.168', {
        roomName: roomName,
        parentNode: document.getElementById('jitsi-container'),
        configOverwrite: {
            startWithAudioMuted: false,
            startWithVideoMuted: false,
            prejoinPageEnabled: false,
            disableDeepLinking: true
        },
        interfaceConfigOverwrite: {
            TOOLBAR_BUTTONS: [
                'microphone', 'camera', 'desktop', 'chat',
                'hangup', 'fullscreen', 'settings'
            ],
            SHOW_JITSI_WATERMARK: false
        }
    });

    // When call ends, optionally return to Tavus
    api.addEventListener('readyToClose', () => {
        document.getElementById('jitsi-container').style.display = 'none';
        document.getElementById('tavus-container').style.display = 'block';
        // Optionally restart Tavus conversation
    });
}
</script>
```

---

### Step 4: Notify Human Agent

When escalation happens, notify an available human agent to join the Jitsi room.

**Option A: Slack notification**
```python
import httpx

async def notify_agent_slack(meeting_url, reason, user_question):
    await httpx.AsyncClient().post(
        "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        json={
            "text": f":rotating_light: *Escalation Request*\n"
                    f"*Reason:* {reason}\n"
                    f"*User asked:* {user_question}\n"
                    f"*Join meeting:* {meeting_url}"
        }
    )
```

**Option B: Agent dashboard via WebSocket**
```javascript
// Agent dashboard listens for new escalations
const ws = new WebSocket('wss://your-backend.com/ws/agent');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    showNotification(`New escalation: ${data.reason}`);
    // Agent clicks to join
    window.open(data.meeting_url, '_blank');
};
```

**Option C: Database queue + polling**
```python
# Store in DB, agent dashboard polls for new requests
async def notify_agent_db(meeting_url, reason, user_question, conversation_id):
    await db.escalations.insert({
        "meeting_url": meeting_url,
        "reason": reason,
        "user_question": user_question,
        "conversation_id": conversation_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    })
```

---

### Step 5: Tavus Persona Prompt Configuration

Update your Tavus persona's system prompt to handle escalation gracefully:

```
You are a helpful AI assistant for Whitelake Digital. You answer questions about
[your domain/products/services].

ESCALATION RULES:
- If the user asks something outside your knowledge, call the escalate_to_human tool
- If the user explicitly asks to speak with a real person, call the escalate_to_human tool
- If the user is frustrated or the conversation is going in circles, call the escalate_to_human tool
- If the topic involves sensitive account issues, billing disputes, or legal matters, call the escalate_to_human tool

ESCALATION BEHAVIOR:
- Before escalating, say: "That's a great question, but I think a member of our team
  would be better suited to help you with this. Let me connect you with someone right now."
- After calling the tool, say: "I've set up a video call for you. A team member will
  join shortly. You'll be redirected to the meeting room now."
- Be warm and reassuring during the handoff
```

---

## End-to-End Flow Summary

```
1. User visits your app
2. Tavus AI avatar starts a video conversation
3. User asks an out-of-scope question
4. Tavus persona's LLM triggers escalate_to_human tool call
5. Tavus sends tool call to your backend webhook
6. Backend creates a unique Jitsi room (e.g., support-a1b2c3d4)
7. Backend notifies human agent with the room link
8. Backend responds to Tavus with the meeting URL
9. Tavus persona tells user: "I'm connecting you with a team member..."
10. Frontend detects the meeting URL and switches from Tavus to Jitsi
11. Human agent joins the same Jitsi room
12. Live 1:1 video call between user and human agent
13. When call ends, user can optionally return to Tavus avatar
```

---

## Jitsi IFrame API Reference

Your Jitsi instance serves the IFrame API at:
```
https://172.83.83.168/external_api.js
```

Include this script in your frontend to embed Jitsi meetings programmatically.

Key API methods:
- `new JitsiMeetExternalAPI(domain, options)` - Create embedded meeting
- `api.executeCommand('hangup')` - End the call
- `api.executeCommand('displayName', 'User Name')` - Set display name
- `api.addEventListener('readyToClose', callback)` - Detect call end
- `api.addEventListener('participantJoined', callback)` - Detect when agent joins
- `api.dispose()` - Clean up the iframe

---

## Notes

- Since we use a self-signed certificate, the Jitsi IFrame API will only work if the user has already accepted the certificate warning. For production, consider adding a domain with Let's Encrypt SSL.
- Tavus API documentation: https://docs.tavus.io
- The `custom_tools` feature in Tavus allows the LLM to call external functions — this is how we trigger the escalation.
- Room names are generated with random IDs to prevent unauthorized access to ongoing calls.
