#!/usr/bin/env bash

# Define user home explicitly since cron runs with a minimal environment
USER_HOME="/app"
PYTHON_BIN="/usr/bin/python3"

# Navigate to the defined home directory
cd "$USER_HOME"

# Infinite loop to keep the script restarting
while true; do
    # Takes control over the SDR and holds for ready 
    usbreset RTL2838UHIDIR
    sleep 2
    
    # Run the first pair of scripts (ignores failures to prevent loop stoppage)
    $PYTHON_BIN "$USER_HOME/ttn.py" || true
    $PYTHON_BIN "$USER_HOME/gif_ttn.py" || true

    # Take a minute break, then take control over the SDR and holds for ready 
    sleep 65
    usbreset RTL2838UHIDIR
    sleep 2
    
    # Run the second pair of scripts
    $PYTHON_BIN "$USER_HOME/here.py" || true
    $PYTHON_BIN "$USER_HOME/gif_here.py" || true

    # Take a 5-minute break before restarting the loop
    sleep 300
done
