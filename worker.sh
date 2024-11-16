#!/usr/bin/env bash
set -e

echo "Starting Scheduler Worker..."
exec arq app.worker.WorkerSettings
