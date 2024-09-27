#!/usr/bin/env bash
set -e

echo "Running migrations..."
python3 init.py
echo "Starting FastAPI server..."
exec fastapi run app/main.py --workers ${NB_WORKERS:-1}
