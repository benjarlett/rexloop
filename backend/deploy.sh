#!/bin/bash

# This script is run by the backend engine to update itself.

# --- Configuration ---
# The directory where the rexloop project is on the Pi.
PROJECT_DIR="/home/patch/rexloop"

# --- Script ---

set -e # Exit immediately if a command exits with a non-zero status.

echo "-- Starting Deployment --"

# 1. Navigate to the project directory
cd "$PROJECT_DIR"

# 2. Pull the latest code from the main branch
echo "-- Pulling latest code from Git... --"
git pull origin main

# 3. Install/update dependencies using the virtual environment
echo "-- Installing Python dependencies... --"
source "$PROJECT_DIR/backend/venv/bin/activate"
pip3 install -r "$PROJECT_DIR/backend/requirements.txt"

# The systemd service has Restart=always, so the engine will restart automatically after this script exits.

echo "-- Deployment Finished --"