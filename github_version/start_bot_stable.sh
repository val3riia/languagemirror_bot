#!/bin/bash

# Script to run the Language Mirror bot in a stable way with proper error logging

# Set up the log directory
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Generate a timestamp for the log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/bot_$TIMESTAMP.log"

echo "Starting Language Mirror Bot..."
echo "Logs will be saved to $LOG_FILE"

# Function to clean up on exit
cleanup() {
    echo "Stopping bot..."
    # Kill any background processes
    [[ -f bot.pid ]] && kill $(cat bot.pid) 2>/dev/null
    rm -f bot.pid
    echo "Bot stopped."
    exit 0
}

# Set up trap to catch termination signals
trap cleanup SIGINT SIGTERM

# Remove any existing PID file
rm -f bot.pid

# Check if a Python virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3.7 or higher."
    exit 1
fi

# Check if the main script exists
if [ ! -f "language_mirror_telebot.py" ]; then
    echo "Error: language_mirror_telebot.py not found."
    exit 1
fi

# Verify environment variables
if [ -z "$TELEGRAM_TOKEN" ]; then
    if [ -f ".env" ]; then
        echo "Loading environment variables from .env file..."
        export $(grep -v '^#' .env | xargs)
    else
        echo "Warning: TELEGRAM_TOKEN not set and .env file not found."
        echo "The bot might not work correctly."
    fi
fi

# Start the bot with proper logging
echo "Running bot in the background..."
nohup python3 language_mirror_telebot.py >> "$LOG_FILE" 2>&1 &

# Save the PID of the bot process
echo $! > bot.pid
BOT_PID=$(cat bot.pid)

echo "Bot started with PID: $BOT_PID"
echo "To stop the bot, press Ctrl+C or run 'kill $BOT_PID'"
echo "To view logs in real-time, run: tail -f $LOG_FILE"

# Keep the script running to easily stop it with Ctrl+C
# but don't consume CPU with a busy loop
while kill -0 $BOT_PID 2>/dev/null; do
    sleep 1
done

echo "Bot process has ended."
cleanup