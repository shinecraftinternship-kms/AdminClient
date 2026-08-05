#!/usr/bin/env bash
# Register the admin server in the Supabase cloud registry.
#
# Usage:
#   ./register_server.sh scanner.example.com          # domain (https, port 443)
#   ./register_server.sh 1.2.3.4 80 http              # IP with explicit port/protocol
#
# This is a manual alternative to the automatic registration done by
# admin/main.py --domain on startup (the normal path).

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/scanner-admin}"
HOST="${1:?usage: register_server.sh <host> [port] [protocol]}"
PORT="${2:-443}"
PROTOCOL="${3:-https}"

if [[ ! -d "$APP_DIR/venv" ]]; then
  echo "[!] venv not found at $APP_DIR/venv" >&2
  exit 1
fi

PYTHONPATH="$APP_DIR/admin" \
  "$APP_DIR/venv/bin/python" - "$HOST" "$PORT" "$PROTOCOL" <<'PY'
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

host, port, protocol = sys.argv[1], int(sys.argv[2]), sys.argv[3]

django.setup()

from scanner_api.supabase_client import register_server_in_registry

register_server_in_registry(host, port, protocol)
print(f"[OK] server_registry -> {protocol}://{host}:{port}")
PY
