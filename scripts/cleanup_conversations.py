#!/usr/bin/env python3
"""
Cleanup script to end all active Tavus conversations.
Run this when you hit "maximum concurrent conversations" error.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tavus_client import list_conversations, end_conversation


async def main():
    print("Fetching active conversations...")

    try:
        result = await list_conversations()
        conversations = result.get("conversations", [])

        if not conversations:
            print("No active conversations found.")
            return

        print(f"Found {len(conversations)} active conversation(s):")
        for conv in conversations:
            conv_id = conv.get("conversation_id", "unknown")
            status = conv.get("status", "unknown")
            print(f"  - {conv_id} (status: {status})")

        print("\nEnding all conversations...")
        for conv in conversations:
            conv_id = conv.get("conversation_id")
            if conv_id:
                try:
                    await end_conversation(conv_id)
                    print(f"  ✓ Ended {conv_id}")
                except Exception as e:
                    print(f"  ✗ Failed to end {conv_id}: {e}")

        print("\nCleanup complete!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
