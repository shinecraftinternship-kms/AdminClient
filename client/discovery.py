import json
import os
import time
import urllib.request
import urllib.error

DISCOVERY_SUPABASE_URL = "https://db.eekerbqgmektmrzjiyyv.supabase.co"
DISCOVERY_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVla2VyYnFnbWVrdG1yemppeXl2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIs"
    "ImlhdCI6MTc3ODc2NjUxNywiZXhwIjoyMDk0MzQyNTE3fQ."
    "-dRCu16Cr-235XkQgX3vwC9HAzi5M4RtoKXxwj2ma6E"
)
DISCOVERY_TABLE = "server_registry"
DISCOVERY_TIMEOUT = 5


def _get_supabase_config():
    supabase_url = os.getenv("SUPABASE_URL", DISCOVERY_SUPABASE_URL)
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", DISCOVERY_SUPABASE_KEY)
    return supabase_url, supabase_key


def discover_admin_url():
    """Query Supabase cloud registry to find the admin server's current URL.

    Returns the admin URL string (e.g. "http://1.2.3.4:80") or None if
    discovery fails or the server is marked inactive.
    """
    supabase_url, supabase_key = _get_supabase_config()
    if not supabase_url or not supabase_key:
        return None

    endpoint = (
        f"{supabase_url}/rest/v1/{DISCOVERY_TABLE}"
        f"?id=eq.admin&select=ip_address,port,protocol,is_active"
    )
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=DISCOVERY_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data:
                return None
            row = data[0]
            if not row.get("is_active"):
                return None
            ip = row.get("ip_address", "")
            port = row.get("port", 80)
            protocol = row.get("protocol", "http")
            if not ip or ip == "0.0.0.0":
                return None
            if (protocol == "https" and port == 443) or (protocol == "http" and port == 80):
                return f"{protocol}://{ip}"
            return f"{protocol}://{ip}:{port}"
    except Exception:
        return None


def register_server(ip_address, port=80, protocol="http"):
    """Register or update the admin server's IP in the Supabase cloud registry.

    Called by the admin server on startup and periodically.
    Uses UPSERT so it creates the row if missing or updates it if present.
    """
    supabase_url, supabase_key = _get_supabase_config()
    if not supabase_url or not supabase_key:
        return False

    endpoint = f"{supabase_url}/rest/v1/{DISCOVERY_TABLE}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = json.dumps({
        "id": "admin",
        "ip_address": ip_address,
        "port": port,
        "protocol": protocol,
        "is_active": True,
        "updated_at": "now()",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=DISCOVERY_TIMEOUT):
            return True
    except Exception:
        return False


def detect_public_ip():
    """Detect this machine's public IP address by querying an external service.

    Tries multiple services for reliability. Returns the IP string or None.
    """
    services = [
        "https://api.ipify.org?format=json",
        "https://httpbin.org/ip",
        "https://ifconfig.me/ip",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "SystemScannerPro/3.0")
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8").strip()
                try:
                    data = json.loads(body)
                    for key in ("ip", "origin"):
                        if key in data:
                            ip = data[key].split(",")[0].strip()
                            if ip:
                                return ip
                except json.JSONDecodeError:
                    ip = body.strip()
                    if ip and all(c.isdigit() or c == "." for c in ip):
                        return ip
        except Exception:
            continue
    return None
