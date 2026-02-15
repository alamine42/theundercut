#!/usr/bin/env bash
set -euo pipefail

echo "▶️  Running Alembic migrations…"
alembic upgrade head

# Sync the current season's calendar so CalendarEvent rows exist locally.
SEASON=$(date -u +"%Y")
echo "▶️  Syncing calendar for season $SEASON"
python -m theundercut.cli sync-calendar "$SEASON"

echo "✅  Bootstrap complete"
