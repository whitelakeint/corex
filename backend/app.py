"""FastAPI backend for the Building Concierge avatar powered by Tavus CVI."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import desc, asc
from sqlalchemy.exc import IntegrityError

from backend import tavus_client, tool_stubs
from backend.config import BACKEND_URL, TAVUS_PERSONA_ID
from backend.models import init_db, get_session, Conversation, extract_visitor_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s  %(levelname)-5s  %(message)s",
)
logger = logging.getLogger("concierge.app")

app = FastAPI(title="Building Concierge API")

# Maps conversation_id -> asyncio.Queue for SSE escalation push
_escalation_queues: dict[str, asyncio.Queue] = {}

# Database connection
db_engine = None
db_session = None


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    global db_engine, db_session
    db_engine = init_db("sqlite:///conversations.db")
    db_session = get_session(db_engine)
    logger.info("Database initialized: conversations.db")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on application shutdown."""
    if db_session:
        db_session.close()
    logger.info("Database connection closed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Serve the frontend
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/conversations", response_class=HTMLResponse)
async def conversations_page():
    """Serve conversation history page."""
    try:
        with open(FRONTEND_DIR / "conversations.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("conversations.html not found")
        return HTMLResponse(content="<h1>Conversation History Page Not Found</h1>", status_code=404)


app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


# ---------------------------------------------------------------------------
# Conversation lifecycle
# ---------------------------------------------------------------------------
@app.post("/api/conversations")
async def create_conversation():
    """Create a new Tavus CVI conversation and return the join URL."""
    if not TAVUS_PERSONA_ID:
        return JSONResponse(
            status_code=500,
            content={"error": "TAVUS_PERSONA_ID not configured. Run scripts/setup_persona.py first."},
        )

    data = await tavus_client.create_conversation(
        persona_id=TAVUS_PERSONA_ID,
        callback_url=f"{BACKEND_URL}/webhooks/tavus",
        custom_greeting="Hello! How may I help you?",
        properties={
            "enable_closed_captions": True,
            "max_call_duration": 600,
            "participant_left_timeout": 30,
            "participant_absent_timeout": 120,
        },
    )

    conversation_id = data.get("conversation_id")
    conversation_url = data.get("conversation_url")

    logger.info("Conversation created: %s", conversation_id)
    return {"conversation_id": conversation_id, "conversation_url": conversation_url}


@app.post("/api/conversations/{conversation_id}/end")
async def end_conversation(conversation_id: str):
    """End an active Tavus conversation."""
    data = await tavus_client.end_conversation(conversation_id)
    logger.info("Conversation ended: %s", conversation_id)
    return data


@app.get("/api/conversations")
async def get_conversations(
    days: str = "7",
    sort: str = "newest",
    format: str = "json"
):
    """Get conversation history with filtering and sorting."""
    try:
        # Build query
        query = db_session.query(Conversation)

        # Time filter
        if days != "all":
            cutoff = datetime.utcnow() - timedelta(days=int(days))
            query = query.filter(Conversation.created_at >= cutoff)

        # Sort
        if sort == "oldest":
            query = query.order_by(asc(Conversation.created_at))
        elif sort == "longest":
            query = query.order_by(desc(Conversation.duration_seconds), desc(Conversation.created_at))
        else:  # newest (default)
            query = query.order_by(desc(Conversation.created_at))

        conversations = query.all()

        # Return CSV format
        if format == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Conversation ID", "Started At", "Ended At", "Duration (seconds)", "Visitor Name", "Recording URL", "Transcript"])

            for conv in conversations:
                # Flatten transcript for CSV
                transcript_data = json.loads(conv.transcript) if conv.transcript else []
                transcript_text = " ".join([f"{msg.get('speaker', 'unknown')}: {msg.get('text', '')}" for msg in transcript_data])

                writer.writerow([
                    conv.id,
                    conv.conversation_id,
                    conv.started_at.isoformat() if conv.started_at else "",
                    conv.ended_at.isoformat() if conv.ended_at else "",
                    conv.duration_seconds or 0,
                    conv.visitor_name or "",
                    conv.recording_url or "",
                    transcript_text
                ])

            output.seek(0)
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=conversations-{timestamp}.csv"}
            )

        # Return JSON format (default)
        result = {
            "conversations": [
                {
                    "id": conv.id,
                    "conversation_id": conv.conversation_id,
                    "started_at": conv.started_at.isoformat() if conv.started_at else None,
                    "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
                    "duration_seconds": conv.duration_seconds,
                    "visitor_name": conv.visitor_name,
                    "recording_url": conv.recording_url,
                    "transcript": json.loads(conv.transcript) if conv.transcript else []
                }
                for conv in conversations
            ],
            "total": len(conversations),
            "filters": {"days": days, "sort": sort}
        }

        return result

    except ValueError as e:
        logger.error(f"Invalid query parameter: {e}")
        return JSONResponse(status_code=400, content={"error": "Invalid query parameter"})
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to fetch conversations"})


@app.get("/api/conversations/{conversation_id}/events")
async def conversation_events(conversation_id: str):
    """SSE stream for real-time events (escalation, etc.)."""
    queue: asyncio.Queue = asyncio.Queue()
    _escalation_queues[conversation_id] = queue

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                if event["type"] == "escalation":
                    break  # One-shot: close after escalation
        except asyncio.TimeoutError:
            yield "event: timeout\ndata: {}\n\n"
        finally:
            _escalation_queues.pop(conversation_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Stubbed tool-call endpoints
# ---------------------------------------------------------------------------
class NotifyResidentRequest(BaseModel):
    resident_name: str
    apartment_number: str
    visitor_purpose: str


class UnlockDoorRequest(BaseModel):
    door_id: str
    duration_seconds: int = 10


class ScheduleTourRequest(BaseModel):
    visitor_name: str
    contact_info: str
    preferred_date: str
    unit_preferences: str = ""


class NotifyManagementRequest(BaseModel):
    reason: str
    urgency: str = "normal"


class LogDeliveryRequest(BaseModel):
    delivery_company: str
    recipient_apartment: str
    package_location: str


class EscalateToHumanRequest(BaseModel):
    reason: str
    user_question: str = ""


@app.post("/api/notify-resident")
async def notify_resident(body: NotifyResidentRequest):
    return tool_stubs.notify_resident(
        resident_name=body.resident_name,
        apartment_number=body.apartment_number,
        visitor_purpose=body.visitor_purpose,
    )


@app.post("/api/unlock-door")
async def unlock_door(body: UnlockDoorRequest):
    return tool_stubs.unlock_door(
        door_id=body.door_id,
        duration_seconds=body.duration_seconds,
    )


@app.post("/api/schedule-tour")
async def schedule_tour(body: ScheduleTourRequest):
    return tool_stubs.schedule_tour(
        visitor_name=body.visitor_name,
        contact_info=body.contact_info,
        preferred_date=body.preferred_date,
        unit_preferences=body.unit_preferences,
    )


@app.post("/api/notify-management")
async def notify_management(body: NotifyManagementRequest):
    return tool_stubs.notify_management(
        reason=body.reason,
        urgency=body.urgency,
    )


@app.post("/api/log-delivery")
async def log_delivery(body: LogDeliveryRequest):
    return tool_stubs.log_delivery(
        delivery_company=body.delivery_company,
        recipient_apartment=body.recipient_apartment,
        package_location=body.package_location,
    )


@app.post("/api/escalate-to-human")
async def escalate_to_human_endpoint(body: EscalateToHumanRequest):
    return tool_stubs.escalate_to_human(
        reason=body.reason,
        user_question=body.user_question,
    )


# ---------------------------------------------------------------------------
# Tavus webhook receiver
# ---------------------------------------------------------------------------
@app.post("/webhooks/tavus")
async def tavus_webhook(request: Request):
    """Receive and log Tavus CVI webhook events."""
    payload = await request.json()
    event_type = payload.get("event_type", "unknown")

    # --- Tool call handling ---
    if event_type in ("tool_call", "conversation.tool_call"):
        tool_name = (
            payload.get("tool_name")
            or payload.get("properties", {}).get("tool_name")
            or payload.get("function", {}).get("name", "")
        )
        arguments = (
            payload.get("arguments")
            or payload.get("properties", {}).get("arguments", {})
        )
        conversation_id = (
            payload.get("conversation_id")
            or payload.get("properties", {}).get("conversation_id", "")
        )

        logger.info("Tool call: %s (conversation %s)", tool_name, conversation_id)

        tool_handlers = {
            "notify_resident": lambda args: tool_stubs.notify_resident(**args),
            "unlock_door": lambda args: tool_stubs.unlock_door(**args),
            "schedule_tour": lambda args: tool_stubs.schedule_tour(**args),
            "notify_management": lambda args: tool_stubs.notify_management(**args),
            "log_delivery": lambda args: tool_stubs.log_delivery(**args),
            "escalate_to_human": lambda args: tool_stubs.escalate_to_human(**args),
        }

        handler = tool_handlers.get(tool_name)
        if handler:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            result = handler(arguments)

            # Push escalation event to SSE queue for frontend
            if tool_name == "escalate_to_human" and conversation_id:
                queue = _escalation_queues.get(conversation_id)
                if queue:
                    await queue.put({
                        "type": "escalation",
                        "data": {
                            "room_id": result["room_id"],
                            "meeting_url": result["meeting_url"],
                            "reason": arguments.get("reason", ""),
                        },
                    })
                    logger.info("Escalation event pushed to SSE for %s", conversation_id)
                else:
                    logger.warning("No SSE listener for conversation %s", conversation_id)

            return {"tool_response": result}

        logger.warning("Unknown tool: %s", tool_name)
        return {"status": "ok", "error": f"Unknown tool: {tool_name}"}

    # --- Other event types ---
    if event_type == "application.transcription_ready":
        transcript = payload.get("properties", {}).get("transcript", "")
        logger.info("Transcript ready: %s", transcript[:200] if isinstance(transcript, str) else "...")

        # Store conversation in database
        try:
            conversation_id = payload["conversation_id"]
            props = payload.get("properties", {})

            # Parse timestamps
            started_at = datetime.fromisoformat(props["started_at"].replace("Z", "+00:00"))
            ended_at = datetime.fromisoformat(props["ended_at"].replace("Z", "+00:00"))
            duration_seconds = int((ended_at - started_at).total_seconds())

            # Process transcript
            transcript_array = props.get("transcript", [])
            transcript_json = json.dumps(transcript_array)

            # Extract visitor name from transcript text
            transcript_text = " ".join([msg.get("content", "") for msg in transcript_array])
            visitor_name = extract_visitor_name(transcript_text)

            # Get recording URL if available
            recording_url = props.get("recording_url")

            # Create and store conversation
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
            logger.info(f"Conversation {conversation_id} already exists, skipping")
        except KeyError as e:
            # Missing required field in webhook payload
            db_session.rollback()
            logger.warning(f"Missing field in transcription webhook: {e}")
        except Exception as e:
            # Unexpected error
            db_session.rollback()
            logger.error(f"Failed to store conversation: {e}")

    elif event_type == "application.recording_ready":
        recording_url = payload.get("properties", {}).get("recording_url", "")
        logger.info("Recording ready: %s", recording_url)

    elif event_type == "system.shutdown":
        conversation_id = payload.get("properties", {}).get("conversation_id", "")
        logger.info("Conversation ended (shutdown): %s", conversation_id)

    else:
        logger.info("Webhook event: %s — %s", event_type, payload)

    return {"status": "ok"}
