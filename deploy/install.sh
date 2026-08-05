#!/usr/bin/env bash
# System Scanner Pro Admin - VPS install script (Debian/Ubuntu)
#
# Usage:
#   DOMAIN=scanner.example.com ./install.sh
#
# Prerequisites:
#   - A VPS reachable from the internet
#   - A DNS A record pointing the domain at this VPS's public IP
#   - The repo copied to /opt/scanner-admin (or set APP_DIR)
#   - A populated .env next to the repo (DATABASE_URL / SUPABASE_URL /
#     SUPABASE_SERVICE_KEY / DJANGO_SECRET_KEY)
#
# Firewall: open TCP 80/443 and UDP 45000 (client auto-discovery).

set -euo pipefail

DOMAIN="${DOMAIN:-scanner.example.com}"
APP_DIR="${APP_DIR:-/opt/scanner-admin}"
APP_USER="scanner"

if [[ "$DOMAIN" == "scanner.example.com" ]]; then
  echo "[!] Set DOMAIN, e.g.  DOMAIN=scanner.example.com $0" >&2
  exit 1
fi
if [[ ! -d "$APP_DIR" ]]; then
  echo "[!] Repo not found at $APP_DIR (copy it there or set APP_DIR)" >&2
  exit 1
fi
if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "[!] $APP_DIR/.env missing (copy .env from the repo)" >&2
  exit 1
fi

echo "==> Installing system packages"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git

echo "==> Creating service user: $APP_USER"
id -u "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

echo "==> Python virtualenv + dependencies"
if [[ ! -d "$APP_DIR/venv" ]]; then
  python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> systemd unit"
sed -e "s|/opt/scanner-admin|$APP_DIR|g" -e "s|scanner.example.com|$DOMAIN|g" \
  "$APP_DIR/deploy/systemd/system-scanner-admin.service" \
  > /etc/systemd/system/system-scanner-admin.service
systemctl daemon-reload
systemctl enable system-scanner-admin
systemctl restart system-scanner-admin
systemctl --no-pager --full status system-scanner-admin || true

echo "==> nginx site"
sed "s|scanner.example.com|$DOMAIN|g" \
  "$APP_DIR/deploy/nginx/scanner.conf" \
  > /etc/nginx/sites-available/scanner.conf
ln -sf /etc/nginx/sites-available/scanner.conf /etc/nginx/sites-enabled/scanner.conf
nginx -t
systemctl reload nginx

echo "==> TLS certificate (certbot)"
certbot --nginx -d "$DOMAIN" --redirect --non-interactive --agree-tos \
  --register-unsafely-without-email || echo "[!] certbot failed - run manually: certbot --nginx -d $DOMAIN"

echo
echo "Done."
echo "  App:      https://$DOMAIN"
echo "  Login:    https://$DOMAIN/login/"
echo "  Firewall: allow TCP 80/443 and UDP 45000"
