"""Stubbed tool-call handlers for demo purposes.

Each function logs the action to the console and returns a simulated response.
In production these would integrate with building management systems.
"""

from __future__ import annotations

import logging
import uuid

from backend.config import JITSI_BASE_URL

logger = logging.getLogger("concierge.tools")


def notify_resident(
    resident_name: str,
    apartment_number: str,
    visitor_purpose: str,
) -> dict:
    logger.info(
        "[STUB] Notifying resident %s in apt %s — purpose: %s",
        resident_name,
        apartment_number,
        visitor_purpose,
    )
    return {
        "status": "notified",
        "message": "Resident has been notified (simulated)",
    }


def unlock_door(door_id: str, duration_seconds: int = 10) -> dict:
    logger.info("[STUB] Unlocking %s for %ds", door_id, duration_seconds)
    return {
        "status": "unlocked",
        "message": "Door unlocked (simulated)",
    }


def schedule_tour(
    visitor_name: str,
    contact_info: str,
    preferred_date: str,
    unit_preferences: str = "",
) -> dict:
    logger.info(
        "[STUB] Tour scheduled for %s on %s (contact: %s, prefs: %s)",
        visitor_name,
        preferred_date,
        contact_info,
        unit_preferences,
    )
    return {"status": "scheduled"}


def notify_management(reason: str, urgency: str = "normal") -> dict:
    logger.info(
        "[STUB] Management notified — reason: %s, urgency: %s",
        reason,
        urgency,
    )
    return {
        "status": "connecting",
        "message": "Connecting you to a staff member now. Please stay on the line.",
    }


def log_delivery(
    delivery_company: str,
    recipient_apartment: str,
    package_location: str,
) -> dict:
    logger.info(
        "[STUB] Delivery logged — %s to apt %s, placed in %s",
        delivery_company,
        recipient_apartment,
        package_location,
    )
    return {"status": "logged"}


def escalate_to_human(reason: str, user_question: str = "") -> dict:
    room_id = "support-lobby"  # Fixed room - all escalations go to the same room
    meeting_url = f"{JITSI_BASE_URL}/{room_id}"

    logger.info(
        "[ESCALATION] Creating Jitsi room %s — reason: %s, question: %s",
        room_id,
        reason,
        user_question,
    )

    return {
        "status": "escalated",
        "room_id": room_id,
        "meeting_url": meeting_url,
        "message": "Okay, connecting you to a real person now. One moment please.",
    }
