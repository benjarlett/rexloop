#!/bin/bash

# This script is run by the backend engine to trigger a full refresh.

set -e # Exit immediately if a command exits with a non-zero status.

echo "-- Triggering full project refresh --"

echo "[DEBUG] Current directory before cd: $(pwd)"
# Navigate to the project root and execute refresh.sh
# The deploy.sh script is executed from the backend directory, so go up one level.
cd ..
echo "[DEBUG] Current directory after cd: $(pwd)"
bash ./refresh.sh

echo "-- Refresh triggered successfully --"