#!/bin/bash
#
# Wrapper script for running email archiving workflows via cron
# Usage: ./run_workflow.sh <workflow_name>
#

# Set up environment
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Change to script directory
cd "$(dirname "$0")"

# Get workflow name from argument
WORKFLOW="$1"

if [ -z "$WORKFLOW" ]; then
    echo "Usage: $0 <workflow_name>"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the workflow with logging
echo "=== Starting $WORKFLOW at $(date) ===" >> "logs/${WORKFLOW}.log" 2>&1
python archive_cli.py run "$WORKFLOW" >> "logs/${WORKFLOW}.log" 2>&1
echo "=== Finished $WORKFLOW at $(date) ===" >> "logs/${WORKFLOW}.log" 2>&1
echo "" >> "logs/${WORKFLOW}.log" 2>&1
