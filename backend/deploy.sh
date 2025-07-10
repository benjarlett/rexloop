#!/bin/bash

# This script is run by the backend engine to trigger a full refresh.

set -e # Exit immediately if a command exits with a non-zero status.

echo "-- Triggering full project refresh --"

echo "[DEBUG] Current directory before executing refresh.sh: $(pwd)"
bash ./refresh.sh

echo "-- Refresh triggered successfully --"