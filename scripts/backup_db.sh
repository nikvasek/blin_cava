#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DB_PATH:-data/cafe.db}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" ]]; then
  echo "DB file not found: $DB_PATH" >&2
  exit 1
fi

ts="$(date +%F_%H-%M-%S)"
cp "$DB_PATH" "$BACKUP_DIR/cafe_${ts}.db"
echo "Backup created: $BACKUP_DIR/cafe_${ts}.db"
