import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client.runtime import is_frozen, get_client_data_dir

CONFIG_PATH = os.path.join(get_client_data_dir(), "client_config.json")
LOCALHOST_URL = "http://localhost:80"


def load_config():
    defaults = {"admin_url": "", "scan_interval": 3600, "auto_start": True}
    try:
        if os.path.exists(CONFIG_PATH):
            import json
            with open(CONFIG_PATH) as f:
                data = json.load(f)
                defaults.update(data)
    except Exception:
        pass
    return defaults


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
      1. Cloud discovery via Supabase (works across any network)
      2. Cached URL from client_config.json
      3. UDP broadcast discovery (LAN only)
      4. Manual prompt (first-time fallback)
    """
    config = load_config()
    cached_url = config.get("admin_url", "")

    try:
        from client.discovery import discover_admin_url
        discovered = discover_admin_url()
        if discovered:
            if discovered != cached_url:
                config["admin_url"] = discovered
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
