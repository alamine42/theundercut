#!/usr/bin/env bash
set -euo pipefail

echo "▶️  Running Alembic migrations…"
alembic upgrade head

# --- optional: sync calendar once migrations are done -------------
# Uncomment after you implement the CLI command in src/theundercut/cli.py
# SEASON=$(date +"%Y")
# echo "▶️  Syncing calendar for season $SEASON"
# python -m theundercut.cli sync-calendar "$SEASON"

echo "✅  Bootstrap complete"
