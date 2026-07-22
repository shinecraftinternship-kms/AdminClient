import sys
import os
import time
import json
import socket
import platform
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("client.main")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from AdminClient.client.runtime import is_frozen, get_client_data_dir
from AdminClient.client.key_manager import load_or_create_key, load_config, save_config, load_or_create_fingerprint
from AdminClient.client.config import prompt_admin_url, discover_admin, load_config, save_config
from AdminClient.client.communicator import Communicator, WebSocketClient

try:
    from AdminClient.client.discovery import discover_admin_url
except ImportError:
    discover_admin_url = None
from AdminClient.client.scanner import collect_all

try:
    from AdminClient.client.metrics import collect_metrics
except ImportError:
    collect_metrics = None

try:
    from AdminClient.client.events.dispatcher import EventDispatcher
    from AdminClient.client.events.usb_monitor import USBMonitor
    from AdminClient.client.events.file_monitor import FileMonitor
    from AdminClient.client.events.process_monitor import ProcessMonitor
    from AdminClient.client.events.software_monitor import SoftwareMonitor
    HAS_EVENT_MONITORS = True
except ImportError:
    HAS_EVENT_MONITORS = False

DISCOVERY_PORT = 45000
VERSION = "1.0.0"
OUTPUT_DIR = os.path.join(get_client_data_dir(), "scans")


def print_header():
    print("=" * 55)
    print(f"  System Scanner Pro Client v{VERSION}")
    print("  Runs on this machine and reports to admin server")
    print("  WebSocket + HTTP fallback communication")
    if HAS_EVENT_MONITORS:
        print("  Event monitoring: USB, File, Process, Software")
    print("=" * 55)
    print()


def save_output(data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"scan_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def display_summary(data):
    if not data or not isinstance(data, dict):
        print("  No scan data available.")
        return
    scan_data = data.get("scan_data") or {}
    hostname = scan_data.get("hostname", "unknown")
    plat = scan_data.get("platform", "unknown")
    ts = scan_data.get("scan_timestamp", data.get("created_at", "unknown"))
    processor = scan_data.get("processor", {})
    ram = scan_data.get("ram", {})
    storage = scan_data.get("storage", {})
    gpu = scan_data.get("gpu", [])
    os_info = scan_data.get("os_info", {})

    print(f"  Hostname:      {hostname}")
    print(f"  Platform:      {plat}")
    print(f"  Scanned at:    {ts}")
    print(f"  CPU:           {processor.get('model', 'N/A')}")
    print(f"  RAM:           {ram.get('capacity_gb', 'N/A')}")
    print(f"  OS:            {os_info.get('version', 'N/A')}")
    gpus = gpu if isinstance(gpu, list) else []
    print(f"  GPU(s):        {', '.join(g.get('name', '') for g in gpus) or 'N/A'}")
    disks = storage.get("disks", [])
    for d in disks:
        print(f"  Disk:          {d.get('model', 'N/A')} ({d.get('size_gb', '?')} GB)")


CLOUD_DISCOVERY_INTERVAL = 300


def cloud_discovery_loop(comm):
    """Periodically check Supabase for admin IP changes."""
    while True:
        time.sleep(CLOUD_DISCOVERY_INTERVAL)
        try:
            if discover_admin_url:
                new_url = discover_admin_url()
                if new_url and new_url != comm.admin_url:
                    if comm.is_reachable(new_url):
                        comm.update_admin_url(new_url)
                        cfg = load_config()
                        cfg["admin_url"] = new_url
                        save_config(cfg)
                        now = datetime.now().strftime('%H:%M:%S')
                        print(f"  [{now}] [DISCOVERY] Admin moved to {new_url}")
        except Exception:
            pass


def listen_admin_broadcast(comm, hostname):
    """Background: listen for ADMIN_HERE UDP broadcasts, update admin URL when discovered."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    sock.settimeout(5)
    while True:
        try:
            data, (ip, _) = sock.recvfrom(1024)
            if data.startswith(b"ADMIN_HERE"):
                parts = data.decode().strip().split(":")
                port = int(parts[1]) if len(parts) > 1 else 80
                discovered = f"http://{ip}:{port}"
                if discovered != comm.admin_url and comm.is_reachable(discovered):
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {discovered}")
                    comm.update_admin_url(discovered)
                    cfg = load_config()
                    cfg["admin_url"] = discovered
                    save_config(cfg)
        except socket.timeout:
            pass
        except Exception:
            pass


def handle_ws_command(command):
    """Callback for commands received via WebSocket."""
    cmd_type = command.get("command_type", "")
    cmd_id = command.get("command_id", "")
    payload = command.get("payload", {})
    now = datetime.now().strftime('%H:%M:%S')

    if cmd_type == "scan_now":
        print(f"  [{now}] [WS] Admin requested scan. Running...")
        scan_data = collect_all()
        result = _global_comm.submit_scan(_global_key, scan_data)
        if result.get("status") == "ok":
            print(f"  [{now}] [WS] Scan submitted successfully!")
            if _global_ws_client:
                _global_ws_client.send_message("scan_result", {
                    "scan_type": "on_demand",
                    "scan_data": {"hostname": socket.gethostname(), "platform": platform.system()},
                })
        else:
            print(f"  [{now}] [WS] Scan failed: {result.get('message', 'Unknown')}")

    elif cmd_type == "config_update":
        interval = payload.get("interval_seconds")
        enabled = payload.get("enabled")
        if interval is not None or enabled is not None:
            print(f"  [{now}] [WS] Config update received")
            cfg = _global_comm.get_scan_config(_global_key)
            if interval is not None:
                cfg["interval_seconds"] = interval
            if enabled is not None:
                cfg["enabled"] = enabled
            _global_scan_config.update(cfg)

    elif cmd_type == "ping":
        if _global_ws_client:
            _global_ws_client.send_message("pong")

    else:
        print(f"  [{now}] [WS] Unknown command: {cmd_type}")


_global_comm = None
_global_key = None
_global_ws_client = None
_global_scan_config = {}
_global_event_dispatchers = []
_global_event_monitors = []


def heartbeat_loop(comm, key, hostname, fingerprint):
    """HTTP heartbeat fallback loop (runs alongside WebSocket).

    Includes exponential backoff on consecutive failures and
    proactive offline queue flushing when connectivity returns.
    """
    global _global_comm, _global_key
    _global_comm = comm
    _global_key = key

    consecutive_errors = 0
    backoff = 5
    monitoring_registered = False
    monitoring_agent_id = None
    monitoring_secret = None
    threading.Thread(target=listen_admin_broadcast, args=(comm, hostname), daemon=True).start()

    while True:
        try:
            resp = comm.ping(key, hostname, VERSION, fingerprint)
            consecutive_errors = 0
            backoff = 5

            if comm._consecutive_failures == 0 and comm._offline_queue:
                sent = comm.flush_offline_queue(key)
                if sent:
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"  [{now}] Flushed {sent} queued events")

            if collect_metrics:
                metrics = collect_metrics()
                if not monitoring_registered:
                    try:
                        import uuid as _uuid
                        monitoring_agent_id = str(_uuid.uuid4())
                        reg_resp = comm.monitor_register(
                            monitoring_agent_id, fingerprint,
                            hostname, platform.system(), VERSION,
                        )
                        if reg_resp.get("secret_key"):
                            monitoring_secret = reg_resp["secret_key"]
                            monitoring_registered = True
                            for d in _global_event_dispatchers:
                                d.set_monitoring_credentials(monitoring_agent_id, monitoring_secret)
                    except Exception as e:
                        logger.debug("Monitoring registration failed: %s", e)

                if monitoring_registered and monitoring_agent_id and monitoring_secret:
                    try:
                        import hmac as _hmac
                        import hashlib as _hashlib
                        import time as _time

                        body = json.dumps(metrics).encode("utf-8")
                        sig = _hmac.new(
                            monitoring_secret.encode("utf-8"), body,
                            _hashlib.sha256,
                        ).hexdigest()

                        comm.monitor_heartbeat(
                            monitoring_agent_id, sig,
                            _time.time(), metrics,
                        )
                    except Exception as e:
                        logger.debug("Heartbeat send failed: %s", e)

            if resp.get("trigger_scan"):
                now = datetime.now().strftime('%H:%M:%S')
                print(f"  [{now}] [HTTP] Admin requested scan. Running...")
                scan_data = collect_all()
                result = comm.submit_scan(key, scan_data)
                if result.get("status") == "ok":
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] [HTTP] Scan submitted successfully!")
                else:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] [HTTP] Scan failed: {result.get('message', 'Unknown')}")
                time.sleep(5)
                continue
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors <= 3:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Heartbeat error: {e}")
            elif consecutive_errors == 5:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Multiple errors - trying cloud discovery...")
                if discover_admin_url:
                    discovered = discover_admin_url()
                    if discovered and discovered != comm.admin_url and comm.is_reachable(discovered):
                        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {discovered}")
                        comm.update_admin_url(discovered)
                        cfg = load_config()
                        cfg["admin_url"] = discovered
                        save_config(cfg)
                        consecutive_errors = 0
                        backoff = 5
                    else:
                        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Cloud discovery failed, trying UDP...")
                        discovered = discover_admin(timeout=2)
                        if discovered and discovered != comm.admin_url and comm.is_reachable(discovered):
                            print(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {discovered}")
                            comm.update_admin_url(discovered)
                            cfg = load_config()
                            cfg["admin_url"] = discovered
                            save_config(cfg)
                            consecutive_errors = 0
                            backoff = 5
                else:
                    discovered = discover_admin(timeout=2)
                    if discovered and discovered != comm.admin_url and comm.is_reachable(discovered):
                        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {discovered}")
                        comm.update_admin_url(discovered)
                        cfg = load_config()
                        cfg["admin_url"] = discovered
                        save_config(cfg)
                        consecutive_errors = 0
                        backoff = 5
            elif consecutive_errors % 10 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Still disconnected ({consecutive_errors} errors). Retrying in {backoff}s...")
        time.sleep(min(backoff, 30))
        backoff = min(backoff * 2, 30)


class HeartbeatWatchdog:
    """Watchdog that monitors the heartbeat thread and restarts it if it dies."""

    def __init__(self, comm, key, hostname, fingerprint):
        self.comm = comm
        self.key = key
        self.hostname = hostname
        self.fingerprint = fingerprint
        self._thread = None
        self._stop = threading.Event()
        self._restart_count = 0

    def start(self):
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _watch_loop(self):
        while not self._stop.is_set():
            if self._thread and not self._thread.is_alive():
                self._restart_count += 1
                now = datetime.now().strftime('%H:%M:%S')
                if self._restart_count > 5:
                    print(f"  [{now}] [WATCHDOG] Too many restarts ({self._restart_count}). Giving up.")
                    break
                print(f"  [{now}] [WATCHDOG] Heartbeat thread died. Restarting (attempt {self._restart_count})...")
                self._thread = threading.Thread(
                    target=heartbeat_loop,
                    args=(self.comm, self.key, self.hostname, self.fingerprint),
                    daemon=True,
                )
                self._thread.start()
            self._stop.wait(10)


def start_websocket_client(comm, monitoring_agent_id, monitoring_secret):
    """Start the WebSocket client for real-time communication."""
    global _global_ws_client

    ws_client = WebSocketClient(
        admin_url=comm.admin_url,
        agent_id=monitoring_agent_id,
        secret_key=monitoring_secret,
        on_command=handle_ws_command,
    )
    _global_ws_client = ws_client
    ws_client.start()
    return ws_client


def _start_event_monitors(comm, key, ws_client):
    """Initialize and start all event monitoring subsystems."""
    global _global_event_dispatchers, _global_event_monitors

    dispatcher = EventDispatcher(
        ws_client=ws_client,
        http_comm=comm,
        client_key=key,
        batch_interval=5,
        max_batch_size=50,
    )
    _global_event_dispatchers.append(dispatcher)

    def on_event(event):
        dispatcher.dispatch(event)

    usb_monitor = USBMonitor(on_event=on_event, poll_interval=5)
    process_monitor = ProcessMonitor(on_event=on_event, poll_interval=10)
    software_monitor = SoftwareMonitor(on_event=on_event, poll_interval=60)

    file_monitor = None
    try:
        file_monitor = FileMonitor(on_event=on_event)
    except Exception as e:
        print(f"  [INFO] File monitor not available: {e}")

    print("  [OK] Taking baselines for change detection...")
    usb_monitor.take_baseline()
    process_monitor.take_baseline()
    software_monitor.take_baseline()

    dispatcher.start()
    usb_monitor.start()
    process_monitor.start()
    software_monitor.start()
    if file_monitor:
        file_monitor.start()

    _global_event_monitors.extend([
        ("USB", usb_monitor),
        ("Process", process_monitor),
        ("Software", software_monitor),
    ])
    if file_monitor:
        _global_event_monitors.append(("File", file_monitor))

    print(f"  [OK] {len(_global_event_monitors)} event monitors active")
    for name, _ in _global_event_monitors:
        print(f"        - {name} monitor")


def main():
    global _global_scan_config

    print_header()

    key = load_or_create_key()
    fingerprint = load_or_create_fingerprint()
    print(f"  Your Registration Key: {key}")
    print(f"  Device Fingerprint:    {fingerprint}")
    print()

    config = load_config()
    admin_url = config.get("admin_url", "")

    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        admin_url = sys.argv[1].rstrip("/")
        config["admin_url"] = admin_url
        save_config(config)
    elif admin_url and admin_url != "http://localhost:80":
        print(f"  Current Admin Server: {admin_url}")
        print()
        print("  Program Change Options:")
        print("  [1] New admin server link")
        print("  [2] Continue")
        print()
        choice = input("  Select option (1/2): ").strip()
        if choice == "1":
            from AdminClient.client.config import prompt_admin_url
            admin_url = prompt_admin_url()
            config["admin_url"] = admin_url
            save_config(config)
            print(f"  Admin server updated to: {admin_url}")
            print()
    else:
        from AdminClient.client.config import get_admin_url
        admin_url = get_admin_url()
        config["admin_url"] = admin_url
        save_config(config)

    hostname = socket.gethostname()

    while True:
        comm = Communicator(admin_url)

        print(f"  Admin Server:  {admin_url}")
        print(f"  Client Key:    {key}")
        print(f"  Fingerprint:   {fingerprint}")
        print(f"  Client Version: {VERSION}")
        print()

        if comm.is_reachable():
            break

        print(f"  [ERROR] Cannot reach admin server at {admin_url}")

        if discover_admin_url:
            print("  Trying cloud discovery...")
            cloud_url = discover_admin_url()
            if cloud_url and cloud_url != admin_url:
                admin_url = cloud_url
                config["admin_url"] = admin_url
                save_config(config)
                continue

        print("  Trying UDP auto-discovery...")
        discovered = discover_admin(timeout=3)
        if discovered:
            print(f"  [OK] Discovered admin server at {discovered}")
            admin_url = discovered
            config["admin_url"] = admin_url
            save_config(config)
            continue

        print("  Auto-discovery failed. Enter URL manually.")
        print()
        admin_url = prompt_admin_url()
        config["admin_url"] = admin_url
        save_config(config)

    print("  Connecting to admin server...")
    result = comm.register(key, hostname, platform.system(), VERSION, fingerprint)

    if result.get("status") in ("ok",):
        if result.get("auto_approved"):
            print("  [OK] Auto-approved by admin server.")
        else:
            print("  [WAITING] Registration sent. Waiting for admin approval...")
            while True:
                time.sleep(5)
                status_res = comm.check_status(key)
                if status_res.get("status") == "approved":
                    print("  [OK] Admin approved registration.")
                    break
                elif status_res.get("status") == "error":
                    pass
    elif result.get("status") == "pending":
        print("  [WAITING] Registration pending admin approval...")
        while True:
            time.sleep(5)
            status_res = comm.check_status(key)
            if status_res.get("status") == "approved":
                print("  [OK] Admin approved registration.")
                break
            elif status_res.get("status") == "error":
                pass
    else:
        print(f"  [WARN] {result.get('message', 'Registration pending')}")

    print()
    print("  Performing initial scan...")
    initial_data = collect_all()
    init_result = comm.submit_scan(key, initial_data)
    if init_result.get("status") == "ok":
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Initial scan submitted successfully!")
    else:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Initial scan failed: {init_result.get('message', 'Unknown')}")
    print()

    monitoring_agent_id = None
    monitoring_secret = None

    try:
        import uuid as _uuid
        monitoring_agent_id = str(_uuid.uuid4())
        reg_resp = comm.monitor_register(
            monitoring_agent_id, fingerprint,
            hostname, platform.system(), VERSION,
        )
        if reg_resp.get("secret_key"):
            monitoring_secret = reg_resp["secret_key"]
            print(f"  [OK] Monitoring agent registered: {monitoring_agent_id[:16]}...")
    except Exception as e:
        print(f"  [WARN] Monitoring agent registration failed: {e}")

    print("  Starting communication channels...")
    print()

    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(comm, key, hostname, fingerprint),
        daemon=True,
    )
    hb_thread.start()

    watchdog = HeartbeatWatchdog(comm, key, hostname, fingerprint)
    watchdog.start()
    print("  [OK] Heartbeat watchdog started")

    cloud_thread = threading.Thread(target=cloud_discovery_loop, args=(comm,), daemon=True)
    cloud_thread.start()
    print(f"  [OK] Cloud discovery refresh every {CLOUD_DISCOVERY_INTERVAL}s")

    if monitoring_agent_id and monitoring_secret:
        print("  Connecting WebSocket for real-time communication...")
        ws_client = start_websocket_client(comm, monitoring_agent_id, monitoring_secret)
        print("  WebSocket client started (auto-reconnect enabled)")
    else:
        print("  [INFO] WebSocket not available (monitoring agent not registered)")
        ws_client = None

    if HAS_EVENT_MONITORS:
        print()
        print("  Starting event monitors...")
        _start_event_monitors(comm, key, ws_client)

    print("  Starting heartbeat loop (every 30 seconds)...")
    print("  Press Ctrl+C to stop.")
    print()

    last_scan = time.time()
    while True:
        try:
            now = datetime.now().strftime('%H:%M:%S')
            config = comm.get_scan_config(key)
            interval = config.get("interval_seconds", 3600)
            enabled = config.get("enabled", True)
            _global_scan_config.update(config)

            elapsed = time.time() - last_scan
            if enabled and elapsed >= interval:
                print(f"  [{now}] Scheduled scan starting...")
                scan_data = collect_all()
                result = comm.submit_scan(key, scan_data)
                if result.get("status") == "ok":
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Scheduled scan submitted!")
                else:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Scan failed: {result.get('message', 'Unknown')}")
                last_scan = time.time()

            result = comm.fetch_latest_scan(key)
            if result and result.get("id"):
                print(f"  [{now}] Scan data received.")
                display_summary(result)
                saved = save_output(result)
                print(f"  Output saved to: {saved}")
            else:
                next_min = max(1, int((interval - elapsed) / 60)) if enabled else 30
                print(f"  [{now}] Waiting... next scan in ~{next_min}m")

        except Exception as e:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        print()

        if enabled:
            next_in = max(1, interval - (time.time() - last_scan))
            time.sleep(min(30, next_in))
        else:
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        for name, monitor in _global_event_monitors:
            try:
                monitor.stop()
                print(f"  [OK] {name} monitor stopped")
            except Exception:
                pass
        for dispatcher in _global_event_dispatchers:
            try:
                dispatcher.stop()
                stats = dispatcher.get_stats()
                print(f"  [OK] Event dispatcher stopped (sent: {stats['events_sent']}, failed: {stats['events_failed']})")
            except Exception:
                pass
        if _global_ws_client:
            _global_ws_client.stop()
        print("  Stopped.")
