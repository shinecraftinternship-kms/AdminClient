#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
ADMIN_DIR="$PROJECT_ROOT/admin"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"

export PYTHONPATH="$ADMIN_DIR:$PROJECT_ROOT:$PARENT_DIR:$PYTHONPATH"

if [ ! -d "$PARENT_DIR/AdminClient" ]; then
  ln -s "$PROJECT_ROOT" "$PARENT_DIR/AdminClient" 2>/dev/null || \
  mkdir -p "$PARENT_DIR/AdminClient" && cp -r "$PROJECT_ROOT"/* "$PARENT_DIR/AdminClient/" 2>/dev/null || true
fi

cd "$ADMIN_DIR"
python manage.py collectstatic --noinput
