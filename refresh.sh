#!/bin/bash

# This script automates the process of refreshing the RexLoop project on the Raspberry Pi.
# It should be run from the project root directory (~/rexloop).

# --- Configuration ---
PROJECT_ROOT="/home/patch/rexloop"
BACKEND_DIR="$PROJECT_ROOT/backend"
SERVICE_NAME="rexloop-backend.service"

# --- Script ---

set -e # Exit immediately if a command exits with a non-zero status.

echo "-- Starting RexLoop Refresh --"

# 1. Stop the backend service
echo "-- Stopping $SERVICE_NAME... --"
sudo systemctl stop "$SERVICE_NAME"

# 2. Navigate to the project root and pull latest code
echo "-- Pulling latest code from Git... --"
cd "$PROJECT_ROOT"
git pull origin main

# 3. Navigate to the backend directory, activate venv, and install dependencies
echo "-- Installing Python dependencies... --"
cd "$BACKEND_DIR"
source "$BACKEND_DIR/venv/bin/activate"
pip3 install -r "$BACKEND_DIR/requirements.txt"

# 4. Restart the backend service
echo "-- Starting $SERVICE_NAME... --"
sudo systemctl start "$SERVICE_NAME"

echo "-- RexLoop Refresh Finished --"
