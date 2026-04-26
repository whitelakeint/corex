#!/usr/bin/env python3
"""Update the Tavus persona context with building info and Q&A content.

Run:
    python -m scripts.update_persona_context
"""

from __future__ import annotations

import asyncio
import sys
import os
from pathlib import Path

# Ensure project root is on the path so `backend.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import TAVUS_API_KEY, TAVUS_PERSONA_ID
from backend import tavus_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILDING_INFO = PROJECT_ROOT / "knowledge-base" / "building_info.txt"
CONCIERGE_QA = PROJECT_ROOT / "knowledge-base" / "concierge_qa.txt"


async def main() -> None:
    if not TAVUS_API_KEY or TAVUS_API_KEY == "your_tavus_api_key_here":
        print("ERROR: Set TAVUS_API_KEY in your .env file before running this script.")
        sys.exit(1)

    if not TAVUS_PERSONA_ID or TAVUS_PERSONA_ID == "your_persona_id_here":
        print("ERROR: Set TAVUS_PERSONA_ID in your .env file before running this script.")
        sys.exit(1)

    building_info = BUILDING_INFO.read_text()
    concierge_qa = CONCIERGE_QA.read_text()

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

    print(f"Updating persona context for {TAVUS_PERSONA_ID}...")
    print(f"  Building info: {len(building_info)} chars")
    print(f"  Concierge Q&A: {len(concierge_qa)} chars")
    print(f"  Combined:      {len(combined)} chars")

    result = await tavus_client.patch_persona(TAVUS_PERSONA_ID, operations)

    print()
    print("Persona context updated successfully!")
    print(f"  persona_id: {result.get('persona_id', TAVUS_PERSONA_ID)}")


if __name__ == "__main__":
    asyncio.run(main())
