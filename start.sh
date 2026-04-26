#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if server is already running
if lsof -ti :8001 >/dev/null 2>&1; then
    echo "Server is already running on port 8001"
    echo "Use ./stop.sh to stop it first"
    exit 1
fi

LOG_FILE="$SCRIPT_DIR/server.log"
PID_FILE="$SCRIPT_DIR/server.pid"

echo "Starting Building Concierge server in background..."
nohup uvicorn backend.app:app --host 0.0.0.0 --port 8001 --reload > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# Wait a moment to check if server started successfully
sleep 2

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ Server started successfully (PID: $SERVER_PID)"
    echo "✓ Running on http://localhost:8001"
    echo "✓ Logs: $LOG_FILE"
    echo "✓ Stop with: ./stop.sh"
else
    echo "✗ Server failed to start. Check $LOG_FILE for details"
    exit 1
fi
