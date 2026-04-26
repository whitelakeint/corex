#!/usr/bin/env python3
"""One-time script: upload knowledge-base documents to Tavus.

Run:
    python -m scripts.upload_documents

Uploads building_info.txt (and optionally the Q&A docx if hosted at a public
URL). Prints the document IDs on success.
"""

from __future__ import annotations

import asyncio
import sys
import os
import time

# Ensure project root is on the path so `backend.*` imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import TAVUS_API_KEY
from backend import tavus_client

# ---------------------------------------------------------------------------
# Configure your document URLs here.
# Tavus requires documents to be reachable via public URL.
# ---------------------------------------------------------------------------

DOCUMENTS = [
    {
        "name": "Building Information — The Meridian",
        "url": "",  # <-- Set to the public URL for knowledge-base/building_info.txt
        "tags": ["concierge", "building-info"],
    },
    {
        "name": "AI Avatar Interactions — Concierge Q&A",
        "url": "",  # <-- Set to the public URL for AI Avatar Interactions.docx
        "tags": ["concierge", "faq"],
    },
]


async def wait_for_processing(document_id: str, timeout: int = 120) -> dict:
    """Poll Tavus until the document finishes processing."""
    start = time.time()
    while time.time() - start < timeout:
        doc = await tavus_client.get_document(document_id)
        status = doc.get("status", "unknown")
        if status == "ready":
            return doc
        if status in ("failed", "error"):
            print(f"  Document {document_id} failed processing: {doc}")
            return doc
        print(f"  Status: {status} — waiting...")
        await asyncio.sleep(5)
    print(f"  Timed out waiting for document {document_id}")
    return {}


async def main() -> None:
    if not TAVUS_API_KEY or TAVUS_API_KEY == "your_tavus_api_key_here":
        print("ERROR: Set TAVUS_API_KEY in your .env file before running this script.")
        sys.exit(1)

    for doc_cfg in DOCUMENTS:
        if not doc_cfg["url"]:
            print(f"SKIP: '{doc_cfg['name']}' — no URL configured.")
            print("  Host the file at a public URL and set it in this script.\n")
            continue

        print(f"Uploading: {doc_cfg['name']}")
        print(f"  URL : {doc_cfg['url']}")
        print(f"  Tags: {doc_cfg['tags']}")

        result = await tavus_client.upload_document(
            name=doc_cfg["name"],
            url=doc_cfg["url"],
            tags=doc_cfg["tags"],
        )

        document_id = result.get("document_id")
        print(f"  document_id: {document_id}")
        print("  Waiting for processing...")

        await wait_for_processing(document_id)
        print(f"  Done.\n")

    print("All uploads complete.")


if __name__ == "__main__":
    asyncio.run(main())
