import sys
import os
import traceback

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)
sys.path.insert(0, os.path.dirname(_script_dir))

_crash_log = os.path.join(os.path.dirname(_script_dir), "client_crash.log")


def _log_crash(msg):
    try:
        with open(_crash_log, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _keep_open_pause():
    try:
        input("\n  Press Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass


_log_crash(f"=== START {__import__('datetime').datetime.now()} ===")
_log_crash(f"frozen={getattr(sys, 'frozen', False)}")
_log_crash(f"executable={sys.executable}")
_log_crash(f"argv={sys.argv}")

try:
    if getattr(sys, "frozen", False):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
        try:
            sys.stderr.reconfigure(line_buffering=True)
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("System Scanner Pro Client")
        except Exception:
            pass
        if "--silent" in sys.argv:
            try:
                import ctypes
                _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if _hwnd:
                    ctypes.windll.user32.ShowWindow(_hwnd, 0)
            except Exception:
                pass

    _log_crash("OK: frozen setup done")

    import time
    import json
    import socket
    import platform
    import logging
    import threading
    from datetime import datetime
    from pathlib import Path

    logger = logging.getLogger("client.main")
    _log_crash("OK: stdlib imports done")

    from client.runtime import is_frozen, get_client_data_dir
    _log_crash("OK: imported client.runtime")

    from client.key_manager import load_or_create_key, load_or_create_fingerprint
    _log_crash("OK: imported client.key_manager (funcs)")

    from client.key_manager import load_config as km_load_config, save_config as km_save_config
    _log_crash("OK: imported client.key_manager (config)")

    from client.config import prompt_admin_url, discover_admin
    _log_crash("OK: imported client.config (funcs)")

    from client.config import load_config as cfg_load_config, save_config as cfg_save_config
    _log_crash("OK: imported client.config (config)")

    from client.communicator import Communicator, WebSocketClient
    _log_crash("OK: imported client.communicator")

except Exception as e:
    _log_crash(f"FATAL IMPORT ERROR: {e}")
    _log_crash(traceback.format_exc())
    print()
    print("  ==========================================")
    print("  FATAL ERROR - Startup import failed")
    print("  ==========================================")
    print(f"  Error: {e}")
    print(f"  Crash log: {_crash_log}")
    print()
    traceback.print_exc()
    print("  ==========================================")
    _keep_open_pause()
    sys.exit(1)

try:
    from client.discovery import discover_admin_url
except (ImportError, Exception):
    discover_admin_url = None

try:
    from client.scanner import collect_all
except Exception as e:
    _log_crash(f"FATAL: scanner import failed: {e}")
    print(f"  FATAL: Cannot import scanner module: {e}", flush=True)
    _keep_open_pause()
    sys.exit(1)

try:
    from client.metrics import collect_metrics
except (ImportError, Exception):
    collect_metrics = None

try:
    from client.events.dispatcher import EventDispatcher
    from client.events.usb_monitor import USBMonitor
    from client.events.file_monitor import FileMonitor
    from client.events.process_monitor import ProcessMonitor
    from client.events.software_monitor import SoftwareMonitor
    HAS_EVENT_MONITORS = True
except (ImportError, Exception):
    HAS_EVENT_MONITORS = False

_log_crash("OK: all imports done")
_log_crash(f"OK: data_dir={get_client_data_dir()}")

DISCOVERY_PORT = 45000
VERSION = "1.1.0"
OUTPUT_DIR = os.path.join(get_client_data_dir(), "scans")


def load_config():
    return cfg_load_config()


def save_config(data):
    return cfg_save_config(data)


def P(msg=""):
    print(msg, flush=True)


def safe_input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        print(flush=True)
        return ""


def print_header():
    P("=" * 55)
    P(f"  System Scanner Pro Client v{VERSION}")
    P("  Runs on this machine and reports to admin server")
    P("  WebSocket + HTTP fallback communication")
    if HAS_EVENT_MONITORS:
        P("  Event monitoring: USB, File, Process, Software")
    P("=" * 55)
    P()


def save_output(data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"scan_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def display_summary(data):
    if not data or not isinstance(data, dict):
        P("  No scan data available.")
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

    P(f"  Hostname:      {hostname}")
    P(f"  Platform:      {plat}")
    P(f"  Scanned at:    {ts}")
    P(f"  CPU:           {processor.get('model', 'N/A')}")
    P(f"  RAM:           {ram.get('capacity_gb', 'N/A')}")
    P(f"  OS:            {os_info.get('version', 'N/A')}")
    gpus = gpu if isinstance(gpu, list) else []
    P(f"  GPU(s):        {', '.join(g.get('name', '') for g in gpus) or 'N/A'}")
    disks = storage.get("disks", [])
    for d in disks:
        P(f"  Disk:          {d.get('model', 'N/A')} ({d.get('size_gb', '?')} GB)")


CLOUD_DISCOVERY_INTERVAL = 300


def cloud_discovery_loop(comm):
    while True:
        time.sleep(CLOUD_DISCOVERY_INTERVAL)
        try:
            if load_config().get("manual_url"):
                continue
            if discover_admin_url:
                new_url = discover_admin_url()
                if new_url and new_url != comm.admin_url:
                    if comm.is_reachable(new_url):
                        comm.update_admin_url(new_url)
                        cfg = load_config()
                        cfg["admin_url"] = new_url
                        save_config(cfg)
                        now = datetime.now().strftime('%H:%M:%S')
                        P(f"  [{now}] [DISCOVERY] Admin moved to {new_url}")
        except Exception:
            pass


def listen_admin_broadcast(comm, hostname):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    sock.settimeout(5)
    while True:
        try:
            data, (ip, _) = sock.recvfrom(1024)
            if data.startswith(b"ADMIN_HERE"):
                if load_config().get("manual_url"):
                    continue
                parts = data.decode().strip().split(":")
                port = int(parts[1]) if len(parts) > 1 else 80
                discovered = f"http://{ip}:{port}"
                if discovered != comm.admin_url and comm.is_reachable(discovered):
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {discovered}")
                    comm.update_admin_url(discovered)
                    cfg = load_config()
                    cfg["admin_url"] = discovered
                    save_config(cfg)
        except socket.timeout:
            pass
        except Exception:
            pass


def _try_rediscover(comm, current_url):
    """Try cloud discovery then UDP discovery to find a live admin server.

    Returns the new admin URL if found and reachable, else None.
    """
    candidates = []
    if discover_admin_url:
        try:
            cloud_url = discover_admin_url()
            if cloud_url:
                candidates.append(cloud_url)
        except Exception:
            pass
    try:
        udp_url = discover_admin(timeout=3)
        if udp_url:
            candidates.append(udp_url)
    except Exception:
        pass
    for url in candidates:
        if url != current_url and comm.is_reachable(url):
            return url
    return None


def handle_ws_command(command):
    cmd_type = command.get("command_type", "")
    payload = command.get("payload", {})
    now = datetime.now().strftime('%H:%M:%S')

    if cmd_type == "scan_now":
        P(f"  [{now}] [WS] Admin requested scan. Running...")
        scan_data = collect_all()
        result = _global_comm.submit_scan(_global_key, scan_data)
        if result.get("status") == "ok":
            P(f"  [{now}] [WS] Scan submitted successfully!")
            if _global_ws_client:
                _global_ws_client.send_message("scan_result", {
                    "scan_type": "on_demand",
                    "scan_data": {"hostname": socket.gethostname(), "platform": platform.system()},
                })
        else:
            P(f"  [{now}] [WS] Scan failed: {result.get('message', 'Unknown')}")

    elif cmd_type == "config_update":
        interval = payload.get("interval_seconds")
        enabled = payload.get("enabled")
        if interval is not None or enabled is not None:
            P(f"  [{now}] [WS] Config update received")
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
        P(f"  [{now}] [WS] Unknown command: {cmd_type}")


_global_comm = None
_global_key = None
_global_ws_client = None
_global_scan_config = {}
_global_event_dispatchers = []
_global_event_monitors = []


def heartbeat_loop(comm, key, hostname, fingerprint):
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
            if not isinstance(resp, dict) or resp.get("status") != "ok":
                raise ConnectionError("ping failed")
            consecutive_errors = 0
            backoff = 5

            if comm._consecutive_failures == 0 and comm._offline_queue:
                sent = comm.flush_offline_queue(key)
                if sent:
                    now = datetime.now().strftime('%H:%M:%S')
                    P(f"  [{now}] Flushed {sent} queued events")

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
                        # Use public HTTP heartbeat (no secret needed)
                        comm.monitor_heartbeat_public(key, metrics)
                    except Exception as e:
                        logger.debug("Public heartbeat send failed: %s", e)

            if resp.get("trigger_scan"):
                now = datetime.now().strftime('%H:%M:%S')
                P(f"  [{now}] [HTTP] Admin requested scan. Running...")
                scan_data = collect_all()
                result = comm.submit_scan(key, scan_data)
                if result.get("status") == "ok":
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] [HTTP] Scan submitted successfully!")
                else:
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] [HTTP] Scan failed: {result.get('message', 'Unknown')}")
                time.sleep(5)
                continue
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors <= 3:
                P(f"  [{datetime.now().strftime('%H:%M:%S')}] Heartbeat error: {e}")
            elif consecutive_errors == 5 or consecutive_errors % 10 == 0:
                P(f"  [{datetime.now().strftime('%H:%M:%S')}] Multiple errors - trying discovery...")
                new_url = _try_rediscover(comm, comm.admin_url)
                if new_url:
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovered admin at {new_url}")
                    comm.update_admin_url(new_url)
                    cfg = load_config()
                    cfg["admin_url"] = new_url
                    save_config(cfg)
                    consecutive_errors = 0
                    backoff = 5
                else:
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] Discovery failed, will keep retrying")
        time.sleep(min(backoff, 30))
        backoff = min(backoff * 2, 30)


class HeartbeatWatchdog:
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
                    P(f"  [{now}] [WATCHDOG] Too many restarts ({self._restart_count}). Giving up.")
                    break
                P(f"  [{now}] [WATCHDOG] Heartbeat thread died. Restarting (attempt {self._restart_count})...")
                self._thread = threading.Thread(
                    target=heartbeat_loop,
                    args=(self.comm, self.key, self.hostname, self.fingerprint),
                    daemon=True,
                )
                self._thread.start()
            self._stop.wait(10)


def start_websocket_client(comm, monitoring_agent_id, monitoring_secret):
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


def _start_event_monitors(comm, key, ws_client, monitoring_agent_id=None, monitoring_secret=None):
    global _global_event_dispatchers, _global_event_monitors

    dispatcher = EventDispatcher(
        ws_client=ws_client,
        http_comm=comm,
        client_key=key,
        batch_interval=5,
        max_batch_size=50,
    )
    # Set monitoring credentials if available
    if monitoring_agent_id and monitoring_secret:
        dispatcher.set_monitoring_credentials(monitoring_agent_id, monitoring_secret)
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
        P(f"  [INFO] File monitor not available: {e}")

    P("  [OK] Taking baselines for change detection...")
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

    P(f"  [OK] {len(_global_event_monitors)} event monitors active")
    for name, _ in _global_event_monitors:
        P(f"        - {name} monitor")


# ── Background / auto-start mode ─────────────────────────────────────────────

SILENT_FLAG = "--silent"
MUTEX_NAME = "Local\\SystemScannerPro_Client_Mutex"
_MUTEX_HANDLE = None


def _hide_console_window():
    """Hide the console window of a frozen exe started at boot (Run key)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def _silent_output():
    """Redirect prints to a log file when running hidden (no console)."""
    try:
        log_path = os.path.join(get_client_data_dir(), "client_agent.log")
        fh = open(log_path, "a", encoding="utf-8")
        sys.stdout = fh
        sys.stderr = fh
    except Exception:
        pass


def _ensure_single_instance():
    """Return False if another client process is already running.

    Uses a Windows named mutex so a boot auto-start (Run key + Startup
    folder) and a manual double-click never spawn duplicate agents.
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return True
    try:
        import ctypes
        _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if not _MUTEX_HANDLE:
            return True
        already_exists = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        return not already_exists
    except Exception:
        return True


def _startup_folder():
    """Return the current user's Windows Startup folder, or None."""
    if sys.platform != "win32":
        return None
    base = os.environ.get("APPDATA", "")
    if not base:
        return None
    folder = os.path.join(
        base, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return folder


def _register_startup_script():
    """Create a hidden launcher in the Startup folder.

    Runs at every login even if the registry Run key is cleared or points to
    a stale path, so the agent always comes back online after a reboot.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    folder = _startup_folder()
    if not folder:
        return False
    try:
        vbs_path = os.path.join(folder, "SystemScannerProClient.vbs")
        exe = sys.executable
        quoted = '"' + exe.replace('"', '""') + '"'
        content = (
            'Set sh = CreateObject("WScript.Shell")\r\n'
            f'sh.Run "{quoted} {SILENT_FLAG}", 0, False\r\n'
        )
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(content)
        _log_crash(f"OK: startup launcher created: {vbs_path}")
        return True
    except Exception as e:
        _log_crash(f"WARN: startup launcher creation failed: {e}")
        return False


def _register_autostart():
    """Register this client exe to start automatically at boot/login.

    Re-registered on EVERY run (silent or not) so the Run key and Startup
    folder launcher always point to the currently running exe, even if the
    exe has been rebuilt or moved to a new folder.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    ok = False
    try:
        import winreg
        exe = sys.executable
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "SystemScannerProClient", 0, winreg.REG_SZ,
                              f'"{exe}" {SILENT_FLAG}')
        _log_crash("OK: autostart registered in Windows Run key")
        ok = True
    except Exception as e:
        _log_crash(f"WARN: autostart registration failed: {e}")
    if _register_startup_script():
        ok = True
    return ok


def main():
    global _global_scan_config

    silent = SILENT_FLAG in sys.argv
    if silent:
        sys.argv = [a for a in sys.argv if a != SILENT_FLAG]
        _hide_console_window()
        _silent_output()
        _log_crash("OK: running in silent/background mode")

    # Always refresh auto-start (Run key + Startup folder) on every run so it
    # points at the current exe even after a rebuild or move.
    _register_autostart()

    if not _ensure_single_instance():
        _log_crash("INFO: another client instance is already running - exiting")
        sys.exit(0)

    _log_crash("OK: main() starting")
    print_header()

    key = load_or_create_key()
    fingerprint = load_or_create_fingerprint()
    P(f"  Your Registration Key: {key}")
    P(f"  Device Fingerprint:    {fingerprint}")
    P()

    config = load_config()
    admin_url = config.get("admin_url", "")

    env_url = os.getenv("ADMIN_SERVER_URL", "").strip()
    if env_url:
        admin_url = env_url.rstrip("/")
        config["admin_url"] = admin_url
        save_config(config)
    elif len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        admin_url = sys.argv[1].rstrip("/")
        config["admin_url"] = admin_url
        save_config(config)
    elif silent:
        if not admin_url or admin_url == "http://localhost:80":
            discovered = False
            if discover_admin_url:
                try:
                    cloud_url = discover_admin_url()
                    if cloud_url:
                        admin_url = cloud_url
                        config["admin_url"] = admin_url
                        save_config(config)
                        P(f"  [OK] Discovered admin server: {admin_url}")
                        discovered = True
                except Exception:
                    pass
            if not discovered:
                udp_url = discover_admin(timeout=3)
                if udp_url:
                    admin_url = udp_url
                    config["admin_url"] = admin_url
                    save_config(config)
                    P(f"  [OK] Discovered admin server: {admin_url}")
            if not admin_url:
                admin_url = "http://localhost:80"
                config["admin_url"] = admin_url
                save_config(config)
                P(f"  Using default: {admin_url}")
    else:
        if admin_url and admin_url != "http://localhost:80":
            P(f"  Using saved admin server: {admin_url}")
            P()
        else:
            P("  " + "=" * 50)
            P("  Admin Server Configuration")
            P("  " + "=" * 50)
            P()
            if admin_url and admin_url != "http://localhost:80":
                P(f"  Current Admin Server: {admin_url}")
            P()
            P("  [1] Use auto-discovered / saved server" + (f" ({admin_url})" if admin_url and admin_url != "http://localhost:80" else ""))
            P("  [2] Enter new admin server URL")
            P("  [3] Continue on localhost")
            P("  [4] Exit")
            P("  " + "=" * 50)
            P()
            choice = safe_input("  Select option [1-4]: ").strip()
            _log_crash(f"OK: user chose '{choice}'")

            if choice == "2":
                admin_url = prompt_admin_url()
                config["admin_url"] = admin_url
                config["manual_url"] = True
                save_config(config)
                P(f"  Admin server set to: {admin_url}")
                P()
            elif choice == "3":
                admin_url = "http://localhost:80"
                config["admin_url"] = admin_url
                config["manual_url"] = True
                save_config(config)
                P(f"  Using localhost: {admin_url}")
                P()
            elif choice == "4":
                P("  Exiting...")
                sys.exit(0)
            elif choice == "1" or choice == "":
                if not admin_url or admin_url == "http://localhost:80":
                    P("  Attempting auto-discovery...")
                    discovered = False
                    if discover_admin_url:
                        try:
                            cloud_url = discover_admin_url()
                            if cloud_url:
                                admin_url = cloud_url
                                config["admin_url"] = admin_url
                                save_config(config)
                                P(f"  [OK] Discovered admin server: {admin_url}")
                                discovered = True
                        except Exception:
                            pass
                    if not discovered:
                        udp_url = discover_admin(timeout=3)
                        if udp_url:
                            admin_url = udp_url
                            config["admin_url"] = admin_url
                            save_config(config)
                            P(f"  [OK] Discovered admin server: {admin_url}")
                            discovered = True
                    if not discovered:
                        admin_url = "http://localhost:80"
                        config["admin_url"] = admin_url
                        save_config(config)
                        P(f"  Using default: {admin_url}")
                else:
                    P(f"  Using saved server: {admin_url}")
                P()
            else:
                P("  Invalid option. Using saved/default server.")
                P()

    hostname = socket.gethostname()
    _log_crash(f"OK: admin_url={admin_url} hostname={hostname}")

    retry_count = 0
    while True:
        comm = Communicator(admin_url)

        P(f"  Admin Server:  {admin_url}")
        P(f"  Client Key:    {key}")
        P(f"  Fingerprint:   {fingerprint}")
        P(f"  Client Version: {VERSION}")
        P()

        if comm.is_reachable():
            _log_crash("OK: server reachable")
            break

        retry_count += 1
        P(f"  [ERROR] Cannot reach admin server at {admin_url}")

        if silent:
            if retry_count >= 3:
                P(f"  Trying to rediscover admin server... (attempt {retry_count})")
                new_url = _try_rediscover(comm, admin_url)
                if new_url:
                    P(f"  [OK] Rediscovered admin server: {new_url}")
                    admin_url = new_url
                    config["admin_url"] = new_url
                    save_config(config)
                    retry_count = 0
                    continue
            P(f"  Retrying in 15s... (attempt {retry_count})")
            time.sleep(15)
            continue

        manual = load_config().get("manual_url")
        if manual:
            P(f"  Keeping manual admin server: {admin_url}")
            if is_frozen() and retry_count < 3:
                wait_time = min(10 * retry_count, 60)
                P(f"  Retrying in {wait_time}s... (attempt {retry_count})")
                time.sleep(wait_time)
                continue
            P("  Manual server unreachable.")
            P()
            P("  " + "=" * 45)
            P("  Options:")
            P("  " + "=" * 45)
            P("  [1] Add new admin server link")
            P("  [2] Continue on localhost")
            P("  [3] Exit")
            P("  " + "=" * 45)
            P()
            choice = safe_input("  Select option [1-3]: ").strip()
            if choice == "1":
                admin_url = prompt_admin_url()
                config["admin_url"] = admin_url
                config["manual_url"] = True
                save_config(config)
            elif choice == "2":
                admin_url = "http://localhost:80"
                config["admin_url"] = admin_url
                config["manual_url"] = True
                save_config(config)
            elif choice == "3":
                P("  Exiting...")
                sys.exit(0)
            else:
                continue

        if discover_admin_url:
            P("  Trying cloud discovery...")
            cloud_url = discover_admin_url()
            if cloud_url and cloud_url != admin_url:
                admin_url = cloud_url
                config["admin_url"] = admin_url
                save_config(config)
                retry_count = 0
                continue

        P("  Trying UDP auto-discovery...")
        discovered = discover_admin(timeout=3)
        if discovered:
            P(f"  [OK] Discovered admin server at {discovered}")
            admin_url = discovered
            config["admin_url"] = admin_url
            save_config(config)
            retry_count = 0
            continue

        if silent:
            P(f"  Retrying in 15s... (attempt {retry_count})")
            time.sleep(15)
            continue

        if is_frozen() and retry_count < 3:
            wait_time = min(10 * retry_count, 60)
            P(f"  Retrying in {wait_time}s... (attempt {retry_count})")
            time.sleep(wait_time)
            continue

        P("  Auto-discovery failed.")
        P()
        P("  " + "=" * 45)
        P("  Options:")
        P("  " + "=" * 45)
        P("  [1] Add new admin server link")
        P("  [2] Continue on localhost")
        P("  [3] Exit")
        P("  " + "=" * 45)
        P()
        choice = safe_input("  Select option [1-3]: ").strip()
        if choice == "1":
            admin_url = prompt_admin_url()
            config["admin_url"] = admin_url
            config["manual_url"] = True
            save_config(config)
        elif choice == "2":
            admin_url = "http://localhost:80"
            config["admin_url"] = admin_url
            save_config(config)
        elif choice == "3":
            P("  Exiting...")
            sys.exit(0)
        else:
            P("  Invalid option. Continuing...")
            P()

    P("  Connecting to admin server...")
    result = comm.register(key, hostname, platform.system(), VERSION, fingerprint)
    _log_crash(f"OK: register result={result}")

    # Check if already approved (either auto_approved or existing approved client)
    if result.get("status") == "ok" and result.get("auto_approved"):
        P("  [OK] Auto-approved by admin server.")
    elif result.get("status") == "pending" and result.get("approved"):
        P("  [OK] Already approved.")
    elif result.get("status") == "ok" and result.get("approved"):
        P("  [OK] Already approved.")
    else:
        P("  [WAITING] Registration sent. Waiting for admin approval...")
        while True:
            time.sleep(2)
            status_res = comm.check_status(key)
            if status_res.get("status") == "approved":
                P("  [OK] Admin approved registration.")
                break
            elif status_res.get("status") == "error":
                pass

    P()
    P("  Performing initial scan...")
    initial_data = collect_all()
    init_result = comm.submit_scan(key, initial_data)
    if init_result.get("status") == "ok":
        P(f"  [{datetime.now().strftime('%H:%M:%S')}] Initial scan submitted successfully!")
    else:
        P(f"  [{datetime.now().strftime('%H:%M:%S')}] Initial scan failed: {init_result.get('message', 'Unknown')}")
    P()

    monitoring_agent_id = None
    monitoring_secret = None

    try:
        import uuid as _uuid
        monitoring_agent_id = str(_uuid.uuid4())
        comm._client_key = key  # Pass client key for monitoring registration
        reg_resp = comm.monitor_register(
            monitoring_agent_id, fingerprint,
            hostname, platform.system(), VERSION,
        )
        if reg_resp.get("secret_key"):
            monitoring_secret = reg_resp["secret_key"]
            P(f"  [OK] Monitoring agent registered: {monitoring_agent_id[:16]}...")
    except Exception as e:
        P(f"  [WARN] Monitoring agent registration failed: {e}")

    if not silent and getattr(sys, "frozen", False):
        # Keep the SAME process running in the background instead of
        # spawning a separate child that could die and take the agent
        # offline forever. Hide the console window and continue here.
        _hide_console_window()
        _silent_output()
        _log_crash("OK: connected; hid console, running in background")
        P("  Connected to admin server. Running in background...")
        P()

    P("  Starting communication channels...")
    P()

    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(comm, key, hostname, fingerprint),
        daemon=True,
    )
    hb_thread.start()

    watchdog = HeartbeatWatchdog(comm, key, hostname, fingerprint)
    watchdog.start()
    P("  [OK] Heartbeat watchdog started")

    cloud_thread = threading.Thread(target=cloud_discovery_loop, args=(comm,), daemon=True)
    cloud_thread.start()
    P(f"  [OK] Cloud discovery refresh every {CLOUD_DISCOVERY_INTERVAL}s")

    if monitoring_agent_id and monitoring_secret:
        # Check if WebSocket is supported (not on Vercel)
        if comm.supports_websocket():
            P("  Connecting WebSocket for real-time communication...")
            ws_client = start_websocket_client(comm, monitoring_agent_id, monitoring_secret)
            P("  WebSocket client started (auto-reconnect enabled)")
        else:
            P("  [INFO] WebSocket not supported on this platform (Vercel), using HTTP polling only")
            ws_client = None
    else:
        P("  [INFO] WebSocket not available (monitoring agent not registered)")
        ws_client = None

    if HAS_EVENT_MONITORS:
        P()
        P("  Starting event monitors...")
        _start_event_monitors(comm, key, ws_client, monitoring_agent_id, monitoring_secret)

    P("  Starting heartbeat loop (every 30 seconds)...")
    P("  Press Ctrl+C to stop.")
    P()
    _log_crash("OK: entering main loop")

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
                P(f"  [{now}] Scheduled scan starting...")
                scan_data = collect_all()
                result = comm.submit_scan(key, scan_data)
                if result.get("status") == "ok":
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] Scheduled scan submitted!")
                else:
                    P(f"  [{datetime.now().strftime('%H:%M:%S')}] Scan failed: {result.get('message', 'Unknown')}")
                last_scan = time.time()

            result = comm.fetch_latest_scan(key)
            if result and result.get("id"):
                P(f"  [{now}] Scan data received.")
                display_summary(result)
                saved = save_output(result)
                P(f"  Output saved to: {saved}")
            else:
                next_min = max(1, int((interval - elapsed) / 60)) if enabled else 30
                P(f"  [{now}] Waiting... next scan in ~{next_min}m")

        except Exception as e:
            P(f"  [{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        P()

        if enabled:
            next_in = max(1, interval - (time.time() - last_scan))
            time.sleep(min(30, next_in))
        else:
            time.sleep(30)


if __name__ == "__main__":
    try:
        _log_crash("OK: __main__ block entered")
        main()
    except KeyboardInterrupt:
        P("\n  Shutting down...")
        for name, monitor in _global_event_monitors:
            try:
                monitor.stop()
                P(f"  [OK] {name} monitor stopped")
            except Exception:
                pass
        for dispatcher in _global_event_dispatchers:
            try:
                dispatcher.stop()
                stats = dispatcher.get_stats()
                P(f"  [OK] Event dispatcher stopped (sent: {stats['events_sent']}, failed: {stats['events_failed']})")
            except Exception:
                pass
        if _global_ws_client:
            _global_ws_client.stop()
        P("  Stopped.")
    except Exception as e:
        _log_crash(f"FATAL RUNTIME ERROR: {e}")
        _log_crash(traceback.format_exc())
        P()
        P("  ==========================================")
        P("  FATAL ERROR - Client crashed")
        P("  ==========================================")
        P(f"  Error: {e}")
        P(f"  Crash log saved to: {_crash_log}")
        P()
        traceback.print_exc()
        P("  ==========================================")
        P()
        _keep_open_pause()
