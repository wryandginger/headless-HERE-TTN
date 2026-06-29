#!/usr/bin/env bash

# Define user home explicitly since cron runs with a minimal environment
USER_HOME="/home/USER"
PYTHON_BIN="/usr/bin/python3"

# Navigate to home directory
cd "$USER_HOME"

# Infinite loop to keep the script restarting
while true; do
    # Run the first pair of scripts (ignores failures to prevent loop stoppage)
    $PYTHON_BIN "$USER_HOME/ttn.py" || true
    $PYTHON_BIN "$USER_HOME/gif_ttn.py" || true

    # Pause for 1 second
    sleep 1

    # Run the second pair of scripts
    $PYTHON_BIN "$USER_HOME/here.py" || true
    $PYTHON_BIN "$USER_HOME/gif_here.py" || true

    # Take a 5-minute break before restarting the loop
    sleep 300
done
