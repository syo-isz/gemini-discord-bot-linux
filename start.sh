#!/bin/bash
# Gemini Discord Bot Startup Script

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration with defaults
LAST_SESSION_FILE="./.last_session"
if [ -f "$LAST_SESSION_FILE" ]; then
    SAVED_SESSION=$(cat "$LAST_SESSION_FILE" | tr -d '\n\r')
fi

SESSION_NAME="${SAVED_SESSION:-${TMUX_SESSION_NAME:-gemini-bot}}"
VENV_PATH="${VENV_PATH:-/home/ubuntu/bot_venv}"
BOT_SCRIPT="./main.py"
GEMINI_CMD="${GEMINI_EXECUTABLE_PATH:-gemini}"

echo "Starting Gemini Discord Bot in directory: $SCRIPT_DIR"

# 1. Ensure tmux session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Creating new tmux session: $SESSION_NAME"
    tmux new-session -d -s "$SESSION_NAME" -n "gemini-chat"
    sleep 1
    # Initialize Gemini CLI
    tmux send-keys -t "$SESSION_NAME:0" -l "$GEMINI_CMD --y"
    tmux send-keys -t "$SESSION_NAME:0" Enter
    echo "Waiting for Gemini to initialize..."
    # We use a simple sleep here for the initial setup
    sleep 5
else
    echo "Reusing existing tmux session: $SESSION_NAME"
fi

# 2. Start Discord Bot
PID_FILE="./bot.pid"
echo "Checking for old bot process via PID file..."

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    # プロセスが存在し、かつ自分のプロジェクトの main.py であるか確認
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Stopping old process (PID: $OLD_PID)..."
        kill "$OLD_PID" || kill -9 "$OLD_PID"
        sleep 1
    fi
fi

# Check if venv exists, if not, try to use system python
if [ -d "$VENV_PATH" ]; then
    PYTHON_BIN="$VENV_PATH/bin/python"
else
    PYTHON_BIN="python3"
fi

echo "Starting Discord Bot with $PYTHON_BIN..."
# 現在のシェルスクリプトの PID ($$) を保存
# exec を使うので、この後の python プロセスも同じ PID を引き継ぐよ
echo $$ > "$PID_FILE"

# Use -u for unbuffered output to see logs in real-time
exec "$PYTHON_BIN" -u "$BOT_SCRIPT"
