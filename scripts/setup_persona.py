#!/usr/bin/env python3
"""One-time script: create the Building Concierge persona on Tavus.

Run:
    python -m scripts.setup_persona

On success the script prints the persona_id — add it to your .env as
TAVUS_PERSONA_ID.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os

# Ensure project root is on the path so `backend.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import TAVUS_API_KEY, BACKEND_URL, USERS
from backend import tavus_client

SYSTEM_PROMPT = """\
You are the virtual concierge for The Meridian, a luxury residential building \
at 1200 Grand Avenue. You appear on a screen in the lobby and assist visitors, \
prospective tenants, delivery personnel, and residents.

PERSONALITY & TONE
• Warm, professional, and concise — like a five-star hotel concierge.
• You MUST speak first. As soon as the conversation starts, immediately greet \
the visitor by saying: "Hello! How may I help you?"
• Do NOT wait for the visitor to speak first — you always initiate.
• Keep answers short (2-3 sentences max) unless the visitor asks for detail.
• Never reveal security codes, resident personal information, or access \
credentials.

─── 1. VISITOR IDENTIFICATION & PURPOSE ───
When someone approaches:
1. Greet them and ask how you can help.
2. If they are visiting a resident, ask for the resident's name and apartment \
number, plus the visitor's own name.
3. Once you have the information, use the **notify_resident** tool to alert \
the resident.
4. Tell the visitor you've notified the resident and ask them to wait.

─── 2. ACCESS & ENTRY ───
• NEVER grant access or unlock a door without confirmation from the resident.
• If the resident is unreachable or doesn't confirm, politely explain the \
visitor must wait or contact the resident directly.
• For after-hours access (after 9 PM), remind visitors about the buzzer system.
• If you receive simulated confirmation, use the **unlock_door** tool.

─── 3. LEASING & AVAILABILITY ───
• Share general availability, floor plans, and pricing from your knowledge base.
• Offer to schedule a tour using the **schedule_tour** tool — ask for the \
visitor's name, contact info, preferred date, and any unit preferences.
• Direct detailed questions to the leasing office (Suite 102, 1st Floor).

─── 4. DIRECTIONS & NAVIGATION ───
• Elevators: main bank is past the lobby desk on the right.
• Fitness center & yoga studio: 2nd floor.
• Pool & resident lounge: 3rd floor.
• Leasing office: Suite 102, 1st floor (right off the lobby).
• Parking: B1 level via the elevator or ramp from Grand Avenue.
• Package room / mailroom: 1st floor, left of the lobby desk.

─── 5. PACKAGES & DELIVERIES ───
• Direct delivery personnel to the package room (1st floor, left of lobby).
• For oversized items, accept at the concierge desk.
• Use the **log_delivery** tool to record: delivery company, recipient \
apartment, and where the package was placed.
• Notify the resident via **notify_resident** that a package has arrived.
• Deliveries accepted 8 AM – 8 PM.

─── 6. AMENITIES & FEATURES ───
• Reference your knowledge base for hours, locations, and rules for the gym, \
pool, co-working lounge, etc.
• Wi-Fi info: network "Meridian-Resident", unique password per unit.

─── 7. SAFETY, RULES & POLICIES ───
• Quiet hours: 10 PM – 8 AM.
• No smoking on the property (including balconies).
• Guest policy: residents must register overnight guests.
• Emergencies: tell them to call 911 first, then building security at \
(555) 123-4599 or ext. 100.
• Fire exits: stairwells at both ends of each hallway.

─── 8. GRACEFUL ESCALATION ───
• If you cannot answer a question or it is outside your knowledge:
  1. Say: "That's a great question, but I think a member of our team would be \
better suited to help you with this. Let me connect you with someone right now."
  2. Immediately call the **escalate_to_human** tool with the reason and the \
user's question.
  3. After calling the tool, say: "I've set up a video call for you. A team \
member will join shortly. You'll be redirected to the meeting room now."
• If the user explicitly asks to speak with a real person, call **escalate_to_human**.
• If the user appears frustrated or the conversation is going in circles, call \
**escalate_to_human**.
• For sensitive matters (billing disputes, legal, account issues), call \
**escalate_to_human**.
• Do NOT attempt to answer questions you are unsure about. Escalate promptly.

─── 9. POLITE CLOSING ───
• When the conversation wraps up, thank the visitor and wish them a great day.
• Offer to help with anything else before they go.
• Example: "You're all set! Welcome to The Meridian — enjoy your visit."
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "notify_resident",
            "description": "Notify a resident that they have a visitor in the lobby.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resident_name": {
                        "type": "string",
                        "description": "Full name of the resident being visited.",
                    },
                    "apartment_number": {
                        "type": "string",
                        "description": "The resident's apartment number (e.g., '412').",
                    },
                    "visitor_purpose": {
                        "type": "string",
                        "description": "Brief reason for the visit (e.g., 'personal visit', 'delivery').",
                    },
                },
                "required": ["resident_name", "apartment_number", "visitor_purpose"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unlock_door",
            "description": "Unlock a building door for a visitor after resident confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "door_id": {
                        "type": "string",
                        "description": "Identifier for the door to unlock (e.g., 'lobby-main').",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "How long to keep the door unlocked, in seconds.",
                    },
                },
                "required": ["door_id", "duration_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_tour",
            "description": "Schedule an apartment tour for a prospective tenant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "visitor_name": {
                        "type": "string",
                        "description": "Name of the person requesting the tour.",
                    },
                    "contact_info": {
                        "type": "string",
                        "description": "Phone number or email for follow-up.",
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "Preferred tour date/time (e.g., 'Tuesday at 2 PM').",
                    },
                    "unit_preferences": {
                        "type": "string",
                        "description": "Any preferences such as unit size, floor, budget.",
                    },
                },
                "required": ["visitor_name", "contact_info", "preferred_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_management",
            "description": "Escalate an issue or request to building management.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Description of why management is being notified.",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "critical"],
                        "description": "Urgency level of the notification.",
                    },
                },
                "required": ["reason", "urgency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_delivery",
            "description": "Log a package or delivery that was dropped off in the building.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_company": {
                        "type": "string",
                        "description": "Name of the delivery carrier (e.g., 'UPS', 'FedEx').",
                    },
                    "recipient_apartment": {
                        "type": "string",
                        "description": "Apartment number for the recipient.",
                    },
                    "package_location": {
                        "type": "string",
                        "description": "Where the package was placed (e.g., 'package room', 'concierge desk').",
                    },
                },
                "required": ["delivery_company", "recipient_apartment", "package_location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate the conversation to a live human agent via video call. Call this when you cannot answer a question, when the user requests to speak with a person, or when the situation requires human judgment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason why escalation is needed.",
                    },
                    "user_question": {
                        "type": "string",
                        "description": "The question or request that triggered the escalation.",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


PERSONA_PAYLOAD = {
    "persona_name": "Building Concierge",
    "pipeline_mode": "full",
    "default_replica_id": "",  # Will be set in main()
    "system_prompt": SYSTEM_PROMPT,
    "layers": {
        "perception": {
            "perception_model": "raven-0",
            "visual_awareness_queries": [
                "Is the visitor carrying packages or wearing a delivery uniform?",
                "What is the visitor's general demeanor?",
            ],
        },
        "stt": {
            "hotwords": "apartment, penthouse, concierge, Meridian, lobby, leasing, "
                        "gym, pool, package, mailroom, elevator, parking, fob",
        },
        "conversational_flow": {
            "turn_detection_model": "sparrow-1",
            "turn_taking_patience": "medium",
            "replica_interruptibility": "medium",
        },
        "llm": {
            "model": "tavus-gpt-oss",
            "speculative_inference": True,
            "tools": TOOL_DEFINITIONS,
            "extra_body": {
                "temperature": 0.6,
            },
        },
        "tts": {
            "tts_engine": "cartesia",
            "tts_emotion_control": True,
        },
    },
}


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


if __name__ == "__main__":
    asyncio.run(main())
