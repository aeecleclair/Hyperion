#!/usr/bin/env bash
set -e

python3 init.py
exec fastapi run app/main.py --workers ${NB_WORKERS:-1} "$@"
