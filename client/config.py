import sys
import os

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)
sys.path.insert(0, os.path.dirname(_this_dir))
from client.runtime import is_frozen, get_client_data_dir

CONFIG_PATH = os.path.join(get_client_data_dir(), "client_config.json")
LOCALHOST_URL = "http://localhost:80"


def extract_admin_info(raw_url):
    """Extract admin username and company slug from a connect URL.
    Returns tuple (username, company_slug) or (None, None) if not a connect URL.
    Example: https://example.com/connect/asdf/asdf/ → ('asdf', 'asdf')
    """
    value = (raw_url or "").strip()
    if not value or "/connect/" not in value.lower():
        return None, None

    try:
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        path = parsed.path.strip("/")
        parts = path.split("/")
        if len(parts) >= 3 and parts[0].lower() == "connect":
            username = parts[1]
            company_slug = parts[2]
            return username, company_slug
    except Exception:
        pass

    return None, None


def normalize_admin_url(raw_url):
    value = (raw_url or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        return value
    from urllib.parse import urlsplit
    parsed = urlsplit(value)
    if "/connect/" in parsed.path.lower():
        return f"{parsed.scheme}://{parsed.netloc}"
    if parsed.path and parsed.path != "/":
        return f"{parsed.scheme}://{parsed.netloc}"
    return f"{parsed.scheme}://{parsed.netloc}"


def load_config():
    defaults = {"admin_url": "", "admin_connect_url": "", "scan_interval": 3600, "auto_start": True, "manual_url": False}
    try:
        if os.path.exists(CONFIG_PATH):
            import json
            with open(CONFIG_PATH) as f:
                data = json.load(f)
                if data.get("admin_url"):
                    raw_admin_url = str(data.get("admin_url") or "").strip()
                    if "/connect/" in raw_admin_url.lower():
                        data["admin_connect_url"] = raw_admin_url.rstrip("/")
                        data["admin_url"] = normalize_admin_url(raw_admin_url)
                defaults.update(data)
                if "manual_url" not in data:
                    url = str(data.get("admin_url") or "").strip()
                    if url and url != LOCALHOST_URL:
                        defaults["manual_url"] = True
    except Exception:
        pass
    return defaults


def get_display_admin_url(raw_url=None):
    value = (raw_url or "").strip()
    config = load_config()

    if value:
        base = normalize_admin_url(value)
        if base:
            return base.rstrip("/")

    saved = (config.get("admin_connect_url") or "").strip()
    if saved:
        base = normalize_admin_url(saved)
        if base:
            return base.rstrip("/")

    base = normalize_admin_url(config.get("admin_url", ""))
    if base:
        return base.rstrip("/")

    return (value or config.get("admin_url", "") or "").strip().rstrip("/")


def save_config(data):
    import json
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    existing = load_config()
    existing.update(data)
    with open(CONFIG_PATH, "w") as f:
        json.dump(existing, f, indent=2)


def get_cached_admin_url():
    config = load_config()
    url = config.get("admin_url", "")
    if url and url != LOCALHOST_URL:
        return url
    return None


def get_admin_url():
    """Resolve the admin URL using a multi-source fallback chain.

    Priority:
      0. ADMIN_SERVER_URL environment variable (if set)
      1. Cloud discovery via Supabase (works across any network)
      2. Cached URL from client_config.json
      3. UDP broadcast discovery (LAN only)
      4. Manual prompt (first-time fallback)
    """
    env_url = os.getenv("ADMIN_SERVER_URL", "").strip()
    if env_url:
        return normalize_admin_url(env_url)

    config = load_config()
    cached_url = normalize_admin_url(config.get("admin_url", ""))

    # A manually-configured admin URL is the user's explicit choice and must
    # win over anything discovered on the network/cloud. Otherwise a client
    # pointed at a local admin panel (e.g. http://192.168.x.x:8000) would be
    # silently redirected to the cloud admin and never show up on the local
    # dashboard the user is actually looking at.
    if config.get("manual_url") and cached_url and cached_url != LOCALHOST_URL:
        return cached_url
    if cached_url == LOCALHOST_URL:
        cached_url = ""

    # Cloud discovery picks the currently registered admin server (works
    # across any network). The cached URL is kept as a fallback when discovery
    # is unavailable.
    try:
        from client.discovery import discover_admin_url
        discovered = discover_admin_url()
        if discovered:
            if discovered != cached_url:
                config["admin_url"] = discovered
                config["manual_url"] = False
                save_config(config)
            return discovered
    except ImportError:
        pass
    except Exception:
        pass

    if cached_url and cached_url != LOCALHOST_URL:
        return cached_url

    udp_url = discover_admin(timeout=3)
    if udp_url:
        config["admin_url"] = udp_url
        save_config(config)
        return udp_url

    return prompt_admin_url()


def _safe_input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        print()
        return ""


def prompt_admin_url():
    print()
    print("  " + "=" * 50)
    print("  Admin Server Configuration")
    print("  " + "=" * 50)
    print()
    print("  1. Add new admin server link")
    print("  2. Continue on localhost")
    print("  3. Exit")
    print()
    while True:
        choice = _safe_input("  Select option [1-3]: ").strip()
        if choice == "1":
            url = _safe_input("  URL (e.g., http://192.168.1.100:80): ").strip()
            if not url:
                print("  No URL entered. Using localhost.")
                return LOCALHOST_URL
            return url.rstrip("/")
        elif choice == "2":
            return LOCALHOST_URL
        elif choice == "3":
            print("  Exiting...")
            sys.exit(0)
        else:
            print("  Invalid option. Please enter 1, 2, or 3.")


DISCOVERY_PORT = 45000


def discover_admin(timeout=2):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    try:
        sock.sendto(b"DISCOVER_ADMIN", ("255.255.255.255", DISCOVERY_PORT))
        while True:
            data, (ip, _) = sock.recvfrom(1024)
            if data.startswith(b"ADMIN_HERE"):
                port = int(data.decode().split(":")[1]) if b":" in data else 80
                return f"http://{ip}:{port}"
    except socket.timeout:
        pass
    except Exception:
        pass
    finally:
        sock.close()
    return None
