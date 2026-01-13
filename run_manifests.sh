#!/bin/bash
#
# Wrapper script for generating manifests and track registry via cron
#

# Set up environment
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Change to script directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Run manifest generation
echo "=== Generating manifests at $(date) ===" >> "logs/manifests.log" 2>&1
python generate_manifests.py >> "logs/manifests.log" 2>&1

# Run track registry generation
echo "=== Generating track registry at $(date) ===" >> "logs/manifests.log" 2>&1
python generate_track_registry.py >> "logs/manifests.log" 2>&1

echo "=== Completed at $(date) ===" >> "logs/manifests.log" 2>&1
echo "" >> "logs/manifests.log" 2>&1
