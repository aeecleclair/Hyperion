#!/usr/bin/env bash
set -e

echo "Running migrations..."
# We set an environment variable to tell workers to avoid initializing the database
# as we want to do it only once before workers are forked from the arbiter
export HYPERION_INIT_DB="False"
python3 init.py

echo "Starting FastAPI server..."
exec fastapi run app/main.py --workers ${NB_WORKERS:-1}
