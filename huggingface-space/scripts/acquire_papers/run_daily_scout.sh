#!/bin/bash
# Daily Paper Scout Wrapper Script
# This script can be called directly or by Ralph Wiggum/scheduler

cd /home/gdubs/copernicus-web-public/huggingface-space

# Activate virtual environment if it exists
if [ -f "paper_acquisition_venv/bin/activate" ]; then
    source paper_acquisition_venv/bin/activate
fi

# Run the daily scout
python3 scripts/acquire_papers/daily_scout_runner.py --config scripts/acquire_papers/daily_scout_config.json

# Exit with the script's exit code
exit $?
