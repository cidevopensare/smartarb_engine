#!/bin/bash

# Generic script to run commands in virtual environment
# Usage: ./scripts/run_in_venv.sh "python3 script.py"

cd /home/smartarb/smartarb_engine

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "💡 Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and run command
source venv/bin/activate

# Execute the command passed as argument
eval "$1"

# Return exit code
exit $?
