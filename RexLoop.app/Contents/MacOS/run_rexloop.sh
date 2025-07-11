#!/bin/bash
# This script simply launches the Python orchestrator.
# All complex logic is handled by orchestrator.py

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/orchestrator.py"
