#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/server.pid"

PID=$(lsof -ti :8001 2>/dev/null || true)

if [ -z "$PID" ]; then
    echo "No server running on port 8001"
    # Clean up stale PID file if it exists
    [ -f "$PID_FILE" ] && rm "$PID_FILE"
else
    kill $PID
    echo "✓ Server stopped (PID $PID)"
    # Clean up PID file
    [ -f "$PID_FILE" ] && rm "$PID_FILE"
fi
