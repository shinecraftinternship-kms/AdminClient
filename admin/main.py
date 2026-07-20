import sys
import os
import json
import socket
import time
import argparse
import django
from pathlib import Path
from django.core.management import call_command

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from AdminClient.shared.runtime import is_frozen, get_app_data_dir, get_resources_dir

DATA_DIR = get_app_data_dir()
RESOURCES_DIR = get_resources_dir()
CONFIG_FILE = os.path.join(DATA_DIR, "admin_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


DISCOVERY_PORT = 45000
CLOUD_REFRESH_INTERVAL = 300


def detect_public_ip():
    """Detect this machine's public IP by querying external services."""
    import urllib.request
    import urllib.error
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


def register_with_cloud_discovery(port, protocol="http"):
    """Register admin's public IP in the Supabase cloud registry."""
    try:
        public_ip = detect_public_ip()
        if not public_ip:
            print("  [WARN] Could not detect public IP for cloud discovery")
            return False
        from AdminClient.admin.scanner_api.supabase_client import register_server_in_registry
        register_server_in_registry(public_ip, port, protocol)
        print(f"  [OK] Registered with cloud discovery: {protocol}://{public_ip}:{port}")
        return True
    except Exception as e:
        print(f"  [WARN] Cloud discovery registration failed: {e}")
        return False


def cloud_discovery_refresh_loop(port, protocol="http"):
    """Periodically re-register public IP in Supabase to handle IP changes."""
    while True:
        time.sleep(CLOUD_REFRESH_INTERVAL)
        try:
            public_ip = detect_public_ip()
            if public_ip:
                from AdminClient.admin.scanner_api.supabase_client import register_server_in_registry
                register_server_in_registry(public_ip, port, protocol)
        except Exception:
            pass


def start_discovery_listener(admin_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    while True:
        try:
            data, client_addr = sock.recvfrom(1024)
            if data.decode().strip() == "DISCOVER_ADMIN":
                sock.sendto(f"ADMIN_HERE:{admin_port}".encode(), client_addr)
        except Exception:
            pass


def start_discovery_broadcaster(admin_port):
    """Periodically broadcast ADMIN_HERE so clients auto-discover without asking."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    time.sleep(3)
    while True:
        try:
            msg = f"ADMIN_HERE:{admin_port}".encode()
            sock.sendto(msg, ("255.255.255.255", DISCOVERY_PORT))
        except Exception:
            pass
        time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description="System Scanner Pro - Admin Panel")
    parser.add_argument("--port", type=int, default=80, help="Server port (default: 80)")
    parser.add_argument("--host", type=str, default=None, help="Bind address")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--username", type=str, default="admin", help="Default admin username")
    parser.add_argument("--password", type=str, default="admin123", help="Default admin password")
    parser.add_argument("--reset", action="store_true", help="Re-ask for IP address")
    args = parser.parse_args()

    print("=" * 55)
    print("  System Scanner Pro Admin Panel v2.1")
    print("  (Django + DRF + Bootstrap 5)")
    print("=" * 55)
    print()

    if not args.host:
        saved = load_config()
        if args.reset or not saved.get("host"):
            args.host = input("Enter the IP address to bind (e.g., 0.0.0.0): ").strip()
            if not args.host:
                args.host = "0.0.0.0"
            save_config({"host": args.host})
        else:
            args.host = saved["host"]
            print(f"  Using saved IP: {args.host}")
            print("  (Run with --reset to change IP)")
            print()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
    if args.host == "0.0.0.0":
        os.environ["DJANGO_ALLOWED_HOSTS"] = "*"
    else:
        os.environ["DJANGO_ALLOWED_HOSTS"] = f"0.0.0.0,127.0.0.1,localhost,{args.host}"
    os.environ["SCANNER_DATA_DIR"] = DATA_DIR

    django.setup()
    os.chdir(RESOURCES_DIR)
    print("  Running database migrations...")
    call_command("migrate", verbosity=0)
    from django.contrib.auth.models import User
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(args.username, "", args.password)
        print(f"  Admin user created: {args.username} / {args.password}")

    from AdminClient.admin.scanner_api.views import ensure_admin_client, admin_self_scan
    admin_key = ensure_admin_client()
    import threading
    threading.Thread(target=admin_self_scan, daemon=True).start()
    print(f"  Admin client key: {admin_key}")
    print()

    print(f"  Dashboard: http://{args.host}:{args.port}")
    print(f"  Login:     http://{args.host}:{args.port}/login/")
    print()

    import webbrowser
    if args.host != "0.0.0.0":
        webbrowser.open(f"http://{args.host}:{args.port}")

    disc_thread = threading.Thread(target=start_discovery_listener, args=(args.port,), daemon=True)
    disc_thread.start()
    bcast_thread = threading.Thread(target=start_discovery_broadcaster, args=(args.port,), daemon=True)
    bcast_thread.start()
    print(f"  UDP discovery active on port {DISCOVERY_PORT} (listen + broadcast)")

    protocol = "https" if args.port == 443 else "http"
    cloud_ok = register_with_cloud_discovery(args.port, protocol)
    if cloud_ok:
        refresh_thread = threading.Thread(
            target=cloud_discovery_refresh_loop,
            args=(args.port, protocol),
            daemon=True,
        )
        refresh_thread.start()
        print(f"  Cloud discovery refresh every {CLOUD_REFRESH_INTERVAL}s")
    print()

    runserver_args = [f"{args.host}:{args.port}", "--noreload"]

    call_command("runserver", *runserver_args)


if __name__ == "__main__":
    main()
