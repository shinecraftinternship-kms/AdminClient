import sys
import os
import traceback
import subprocess
import urllib.request

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
    import io

    if getattr(sys, "frozen", False):
        try:
            if isinstance(sys.stdout, io.TextIOWrapper):
                sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
        try:
            if isinstance(sys.stderr, io.TextIOWrapper):
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

    from client.config import prompt_admin_url, discover_admin, get_display_admin_url, get_base_admin_url
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
VERSION = "1.7.0"
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
    ram_info = ram.get('capacity_gb', 'N/A')
    stick_count = ram.get('stick_count', 0)
    if stick_count > 1:
        ram_info += f" ({stick_count} sticks)"
    P(f"  RAM:           {ram_info}")
    P(f"  OS:            {os_info.get('version', 'N/A')}")
    gpus = gpu if isinstance(gpu, list) else []
    P(f"  GPU(s):        {', '.join(g.get('name', '') for g in gpus) or 'N/A'}")
    disks = storage.get("disks", [])
    for d in disks:
        P(f"  Disk:          {d.get('model', 'N/A')} ({d.get('size_gb', '?')} GB)")
    monitors = scan_data.get("peripherals", {}).get("monitors", [])
    if monitors:
        P(f"  Monitor(s):    {len(monitors)} connected")


CLOUD_DISCOVERY_INTERVAL = 300


def cloud_discovery_loop(comm):
    while True:
        time.sleep(CLOUD_DISCOVERY_INTERVAL)
        try:
            if discover_admin_url and not load_config().get("manual_url"):
                new_url = discover_admin_url()
                if new_url and new_url != comm.admin_url:
                    if comm.is_reachable(new_url):
                        comm.update_admin_url(new_url)
                        cfg = load_config()
                        cfg["admin_url"] = new_url
                        cfg["manual_url"] = False
                        save_config(cfg)
                        now = datetime.now().strftime('%H:%M:%S')
                        P(f"  [{now}] [DISCOVERY] Admin moved to {new_url}")
        except Exception:
            pass


def listen_admin_broadcast(comm):
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
    comm = _global_comm
    key = _global_key
    if comm is None or key is None:
        P("  [WS] Command ignored: communication channel is not ready")
        return

    cmd_type = command.get("command_type", "")
    payload = command.get("payload", {})
    now = datetime.now().strftime('%H:%M:%S')

    if cmd_type == "scan_now":
        P(f"  [{now}] [WS] Admin requested scan. Running...")
        scan_data = collect_all()
        result = comm.submit_scan(key, scan_data)
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
            cfg = comm.get_scan_config(key)
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


def _get_executable_path():
    """Return the path of the currently running executable."""
    if getattr(sys, 'frozen', False):
        return os.path.abspath(sys.executable)
    return os.path.abspath(__file__)


def _perform_self_update(download_url, latest_version, is_mandatory=False):
    """Download the new binary and restart via a self-replace script.

    On Windows: creates a .bat that replaces the old exe and restarts it.
    On Linux/macOS: creates a .sh that replaces the old binary and restarts it.
    """
    import tempfile
    import hashlib

    current_path = _get_executable_path()
    is_windows = sys.platform == "win32"

    now = datetime.now().strftime('%H:%M:%S')
    P(f"  [{now}] [UPDATE] Downloading v{latest_version}...")

    try:
        # Determine download platform
        if is_windows:
            dl_platform = "windows"
        elif sys.platform == "darwin":
            dl_platform = "macos"
        else:
            dl_platform = "linux"

        url = f"{download_url}?platform={dl_platform}"

        # Download to temp file
        tmp_dir = tempfile.gettempdir()
        tmp_ext = ".exe" if is_windows else ""
        tmp_file = os.path.join(tmp_dir, f"system_scanner_update{tmp_ext}")

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SystemScannerClient/1.0")
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(tmp_file, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)

        # Verify downloaded file is not empty
        if os.path.getsize(tmp_file) < 1024:
            P(f"  [{now}] [UPDATE] Downloaded file too small - aborting update")
            return False

        file_hash = hashlib.sha256()
        with open(tmp_file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                file_hash.update(chunk)
        P(f"  [{now}] [UPDATE] Download complete. SHA-256: {file_hash.hexdigest()[:16]}...")

        # Create self-replace script
        if is_windows:
            bat_content = f"""@echo off
timeout /t 2 /nobreak >nul
move /y "{tmp_file}" "{current_path}" >nul 2>&1
if %errorlevel% equ 0 (
    echo Update successful - restarting...
    start "" "{current_path}"
) else (
    echo Update failed - keeping old version
    del "%~f0"
)
del "%~f0"
"""
            bat_file = os.path.join(tmp_dir, "system_scanner_update.bat")
            with open(bat_file, "w") as f:
                f.write(bat_content)
            P(f"  [{now}] [UPDATE] Applying update and restarting...")
            os.startfile(bat_file)
        else:
            sh_content = f"""#!/bin/bash
sleep 2
cp "{tmp_file}" "{current_path}"
chmod +x "{current_path}"
if [ $? -eq 0 ]; then
    echo "Update successful - restarting..."
    nohup "{current_path}" > /dev/null 2>&1 &
fi
rm -f "{tmp_file}"
rm -f "$0"
"""
            sh_file = os.path.join(tmp_dir, "system_scanner_update.sh")
            with open(sh_file, "w") as f:
                f.write(sh_content)
            os.chmod(sh_file, 0o755)
            P(f"  [{now}] [UPDATE] Applying update and restarting...")
            subprocess.Popen(["bash", sh_file])

        # Exit current process
        if is_mandatory:
            P(f"  [{now}] [UPDATE] Mandatory update applied - restarting now.")
        else:
            P(f"  [{now}] [UPDATE] Update applied - restarting.")
        sys.exit(0)

    except Exception as e:
        P(f"  [{now}] [UPDATE] Update failed: {e}")
        return False


def heartbeat_loop(comm, key, hostname, fingerprint):
    global _global_comm, _global_key
    _global_comm = comm
    _global_key = key

    consecutive_errors = 0
    backoff = 5
    monitoring_registered = False
    monitoring_agent_id = None
    monitoring_secret = None
    approval_ok = True
    _heartbeat_count = 0
    _last_update_check = 0
    threading.Thread(target=listen_admin_broadcast, args=(comm,), daemon=True).start()

    while True:
        try:
            resp = comm.ping(key, hostname, VERSION, fingerprint)
            just_registered = False
            if not isinstance(resp, dict) or resp.get("status") != "ok":
                missing = isinstance(resp, dict) and "not found" in str(resp.get("message", "")).lower()
                if missing:
                    reg = comm.register(key, hostname, platform.system(), VERSION, fingerprint)
                    if reg and reg.get("status") != "error":
                        resp = dict(reg)
                        resp["approved"] = resp.get("approved", False)
                        resp["status"] = "pending" if not resp.get("approved") else "ok"
                        just_registered = True
                    else:
                        raise ConnectionError("re-register failed")
                else:
                    raise ConnectionError("ping failed")
            consecutive_errors = 0
            backoff = 5

            if resp.get("approved") is False:
                if approval_ok:
                    P("  [WAITING] Approval removed by admin - waiting for re-approval...")
                    approval_ok = False
                if not just_registered:
                    reg = comm.register(key, hostname, platform.system(), VERSION, fingerprint)
                    if reg and reg.get("approved"):
                        approval_ok = True
                        P("  [OK] Admin re-approved registration.")
            elif resp.get("approved") is True:
                if not approval_ok:
                    P("  [OK] Admin approved registration.")
                approval_ok = True

            if comm._consecutive_failures == 0 and comm._offline_queue:
                sent = comm.flush_offline_queue(key)
                if sent:
                    now = datetime.now().strftime('%H:%M:%S')
                    P(f"  [{now}] Flushed {sent} queued events")

            _heartbeat_count += 1
            if resp.get("update_available") and _heartbeat_count - _last_update_check >= 10:
                _last_update_check = _heartbeat_count
                download_url = resp.get("download_url", "")
                if download_url:
                    now = datetime.now().strftime('%H:%M:%S')
                    latest = resp.get("latest_version", "")
                    P(f"  [{now}] [UPDATE] New version available: v{latest}")
                    _perform_self_update(
                        download_url, latest,
                        is_mandatory=resp.get("is_mandatory", False),
                    )

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
        time.sleep(3)
        backoff = 3


class HeartbeatWatchdog:
    def __init__(self, hb_thread, comm, key, hostname, fingerprint):
        self.hb_thread = hb_thread
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
            if self.hb_thread and not self.hb_thread.is_alive():
                self._restart_count += 1
                now = datetime.now().strftime('%H:%M:%S')
                if self._restart_count > 5:
                    P(f"  [{now}] [WATCHDOG] Too many restarts ({self._restart_count}). Waiting 60s before retry...")
                    self._stop.wait(60)
                    continue
                P(f"  [{now}] [WATCHDOG] Heartbeat thread died. Restarting (attempt {self._restart_count})...")
                self.hb_thread = threading.Thread(
                    target=heartbeat_loop,
                    args=(self.comm, self.key, self.hostname, self.fingerprint),
                    daemon=True,
                )
                self.hb_thread.start()
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
RESCUE_FLAG = "--rescue"
_CONSOLE_CTRL_HANDLER = None


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


def _detach_console():
    """Fully detach this process from its console window.

    After this, closing the terminal window does NOT kill the agent: the
    process keeps running in the background. This is what keeps the client
    online and scanning after the exe window closes once approved.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass


def _spawn_background():
    """Start a fully detached hidden copy of this exe (no console window).

    In a PyInstaller onefile build, the app runs as a child of the bootloader
    which keeps the console window attached, so calling FreeConsole() inside
    the app never closes the terminal. The reliable way to close the terminal
    and keep the agent running is to spawn a hidden detached copy here and let
    this process exit. The copy runs with --rescue --silent so it skips the
    single-instance check (the exiting process still holds the mutex) and
    continues the agent in the background.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    try:
        import subprocess
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.Popen(
            [sys.executable, RESCUE_FLAG, SILENT_FLAG],
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True
    except Exception:
        return False


def _launch_rescue():
    """Start a fully detached background copy of this exe.

    Called when the user closes the console window before the agent has moved
    to the background, so the client does not go offline just because the
    terminal was closed.
    """
    return _spawn_background()


def _install_console_close_handler():
    """If the user closes the console window (X button), spawn a detached
    background copy so the agent keeps running instead of going offline."""
    global _CONSOLE_CTRL_HANDLER
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        CTRL_CLOSE_EVENT = 2
        HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)

        @HandlerRoutine
        def _handler(ctrl_type):
            if ctrl_type == CTRL_CLOSE_EVENT:
                _launch_rescue()
            return True

        _CONSOLE_CTRL_HANDLER = _handler
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler, 1)
    except Exception:
        pass


def _silent_output():
    """Redirect prints to a log file when running hidden (no console)."""
    try:
        log_path = os.path.join(get_client_data_dir(), "client_agent.log")
        fh = open(log_path, "a", encoding="utf-8")
        sys.stdout = fh
        sys.stderr = fh
        return
    except Exception:
        pass
    try:
        sys.stdout = open(os.devnull, "w")
        sys.stderr = sys.stdout
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
    Returns the path to the created .vbs launcher, or None on failure.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return None
    folder = _startup_folder()
    if not folder:
        return None
    try:
        vbs_path = os.path.join(folder, "SystemScannerProClient.vbs")
        exe = sys.executable
        # WScript.Shell.Run cannot resolve quoted paths that contain
        # consecutive double spaces (e.g. "admin-client  main\..."), failing
        # with "file not found" (80070002) at boot. Wrapping the command in
        # cmd /c with doubled quotes handles any path spacing correctly.
        content = (
            "Set sh = CreateObject(\"WScript.Shell\")\r\n"
            f'sh.Run "cmd /c """"{exe}"""" {SILENT_FLAG}", 0, False\r\n'
        )
        # newline="" disables universal newline translation, otherwise Python
        # on Windows turns the "\n" into "\r\n" and we get "\r\r\n" output.
        with open(vbs_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        _log_crash(f"OK: startup launcher created: {vbs_path}")
        return vbs_path
    except Exception as e:
        _log_crash(f"WARN: startup launcher creation failed: {e}")
        return None


def _register_autostart():
    """Register this client exe to start automatically at boot/login.

    Re-registered on EVERY run (silent or not) so the Run key and Startup
    folder launcher always point to the currently running exe, even if the
    exe has been rebuilt or moved to a new folder.

    Both the Run key and the Startup folder launch the exe through the
    hidden .vbs launcher (wscript, window style 0) so NO console window is
    ever shown at login - the agent starts fully hidden in the background.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    ok = False
    vbs_path = _register_startup_script()
    try:
        import winreg
        if vbs_path:
            launch = f'wscript.exe "{vbs_path}"'
        else:
            launch = f'"{sys.executable}" {SILENT_FLAG}'
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "SystemScannerProClient", 0, winreg.REG_SZ,
                              launch)
        _log_crash("OK: autostart registered in Windows Run key (hidden)")
        ok = True
    except Exception as e:
        _log_crash(f"WARN: autostart registration failed: {e}")
    if vbs_path:
        ok = True
    return ok


def main():
    global _global_scan_config

    rescue = RESCUE_FLAG in sys.argv
    if rescue:
        sys.argv = [a for a in sys.argv if a != RESCUE_FLAG]
        # The process that spawned us is dying (console closed); wait for it
        # to release the single-instance mutex before we take over.
        time.sleep(3)

    silent = SILENT_FLAG in sys.argv
    if silent:
        sys.argv = [a for a in sys.argv if a != SILENT_FLAG]
        _silent_output()
        _detach_console()
        _log_crash("OK: running in silent/background mode")

    # Always refresh auto-start (Run key + Startup folder) on every run so it
    # points at the current exe even after a rebuild or move.
    _register_autostart()

    if not rescue:
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
    admin_url = config.get("admin_url", "") or config.get("admin_connect_url", "")
    display_admin_url = get_display_admin_url(admin_url)

    env_url = os.getenv("ADMIN_SERVER_URL", "").strip()
    if env_url:
        admin_url = normalize_admin_url(env_url)
        config["admin_url"] = admin_url
        config["admin_connect_url"] = env_url.rstrip("/") if "/connect/" in env_url.lower() else ""
        config["manual_url"] = True
        save_config(config)
        display_admin_url = get_display_admin_url(config.get("admin_connect_url") or admin_url)
    elif len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        raw_url = sys.argv[1].rstrip("/")
        admin_url = normalize_admin_url(raw_url)
        config["admin_url"] = admin_url
        config["admin_connect_url"] = raw_url if "/connect/" in raw_url.lower() else ""
        config["manual_url"] = True
        save_config(config)
        display_admin_url = get_display_admin_url(config.get("admin_connect_url") or admin_url)
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
        # Manual run: ALWAYS ask so the user can continue with the saved
        # server or switch to a new one. This prompt only appears when the
        # exe is launched by hand - boot autostart runs with --silent and
        # never asks.
        P("  " + "=" * 50)
        P("  Admin Server Configuration")
        P("  " + "=" * 50)
        P()
        if display_admin_url and display_admin_url != "http://localhost:80":
            P(f"  Current Admin Server: {display_admin_url}")
        P()
        P("  [1] Continue with this admin server" + (f" ({display_admin_url})" if display_admin_url and display_admin_url != "http://localhost:80" else ""))
        P("  [2] Enter new admin server URL")
        P("  [3] Continue on localhost")
        P("  [4] Exit")
        P("  " + "=" * 50)
        P()
        choice = safe_input("  Select option [1-4] or paste a URL: ").strip()
        _log_crash(f"OK: user chose '{choice}'")

        # Check if user pasted a URL directly (starts with http:// or https://)
        if choice.startswith(("http://", "https://")):
            new_url = choice
            admin_url = normalize_admin_url(new_url)
            config["admin_url"] = admin_url
            config["admin_connect_url"] = new_url.rstrip("/") if "/connect/" in new_url.lower() else ""
            config["manual_url"] = True
            save_config(config)
            display_admin_url = get_display_admin_url(config.get("admin_connect_url") or admin_url)
            P(f"  Admin server set to: {display_admin_url}")
            P()
        elif choice == "2":
            new_url = safe_input("  Enter admin server URL (e.g., http://192.168.1.100:80): ").strip()
            if not new_url:
                P("  No URL entered. Keeping current server.")
                P()
            else:
                admin_url = normalize_admin_url(new_url)
                config["admin_url"] = admin_url
                config["admin_connect_url"] = new_url.rstrip("/") if "/connect/" in new_url.lower() else ""
                config["manual_url"] = True
                save_config(config)
                display_admin_url = get_display_admin_url(config.get("admin_connect_url") or admin_url)
                P(f"  Admin server set to: {display_admin_url}")
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
            if admin_url and admin_url != "http://localhost:80":
                P(f"  Continuing with: {admin_url}")
                P()
            else:
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
                P()
        else:
            P("  Invalid option. Using saved/default server.")
            P()

    try:
        from client.config import get_base_admin_url
        base_url = get_base_admin_url(admin_url)
        if base_url and base_url != admin_url and Communicator(base_url).is_reachable():
            config["admin_url"] = admin_url
            config["admin_base_url"] = base_url
            save_config(config)
    except Exception:
        pass

    hostname = socket.gethostname()
    _log_crash(f"OK: admin_url={admin_url} hostname={hostname}")

    if not silent:
        # If the user closes the terminal (X button) before the agent detaches
        # itself, spawn a detached background copy so the client stays online.
        _install_console_close_handler()

    retry_count = 0
    connect_url = str(config.get("admin_connect_url") or admin_url or "").strip()
    current_server_url = admin_url or connect_url
    display_url = get_display_admin_url(current_server_url)
    base_request_url = get_base_admin_url(current_server_url) or current_server_url
    while True:
        comm = Communicator(base_request_url)

        P(f"  Admin Server:  {display_url or current_server_url}")
        P(f"  Client Key:    {key}")
        P(f"  Fingerprint:   {fingerprint}")
        P(f"  Client Version: {VERSION}")
        P()

        if comm.is_reachable():
            _log_crash("OK: server reachable")
            break

        retry_count += 1
        P(f"  [ERROR] Cannot reach admin server at {display_url or current_server_url}")

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
                admin_url = normalize_admin_url(prompt_admin_url())
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
            admin_url = normalize_admin_url(prompt_admin_url())
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

    # Keep the original connect URL for admin/company context, while using the
    # base host for HTTP requests.
    from client.config import extract_admin_info
    connect_url = str(config.get("admin_connect_url") or admin_url or "").strip()
    admin_username, company_slug = extract_admin_info(connect_url or admin_url)
    if not admin_username and "/connect/" in str(admin_url or "").lower():
        admin_username, company_slug = extract_admin_info(admin_url)

    result = comm.register(key, hostname, platform.system(), VERSION, fingerprint,
                          admin_username=admin_username, company_slug=company_slug)
    _log_crash(f"OK: register result={result}")

    # Only consider approved if the server explicitly says so AND
    # status is "ok". Never trust auto_approved from the server -
    # only an explicit admin approval counts.
    approved = bool(result.get("status") == "ok" and result.get("approved") is True)
    if not approved:
        P("  [WAITING] Registration sent. Waiting for admin approval...")
        P(f"  [WAITING] Approve this device in the admin panel (key: {key})")
        while True:
            time.sleep(2)
            # Keep last_seen fresh while approval is pending. The status
            # endpoint only reads state and cannot tell the admin panel that
            # this background client is still alive.
            status_res = comm.ping(key, hostname, VERSION, fingerprint)
            if status_res.get("status") == "approved" or status_res.get("approved") is True:
                P("  [OK] Admin approved registration.")
                break
            elif status_res.get("status") == "error":
                comm.register(
                    key, hostname, platform.system(), VERSION, fingerprint,
                    admin_username=admin_username, company_slug=company_slug,
                )
    else:
        P("  [OK] Already approved by admin.")

    P()
    P("  Starting heartbeat (keeps client online)...")
    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(comm, key, hostname, fingerprint),
        daemon=True,
    )
    hb_thread.start()
    P("  [OK] Heartbeat thread started")

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
        comm._client_key = key
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
        try:
            comm.ping(key, hostname, VERSION, fingerprint)
        except Exception:
            pass
        if _spawn_background():
            P("  Connected to admin server. Moving to background...")
            _log_crash("OK: spawned background agent; closing terminal")
            for _ in range(5):
                try:
                    comm.ping(key, hostname, VERSION, fingerprint)
                except Exception:
                    pass
                time.sleep(1)
            return
        _silent_output()
        _detach_console()
        _log_crash("WARN: could not spawn background agent; continuing in place")
        P("  Connected to admin server. Running in background...")
        P()

    P("  Starting additional communication channels...")
    P()

    watchdog = HeartbeatWatchdog(hb_thread, comm, key, hostname, fingerprint)
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

    P("  Entering main loop...")
    P("  Press Ctrl+C to stop.")
    P()
    _log_crash("OK: entering main loop")

    last_scan = time.time()
    while True:
        try:
            now = datetime.now().strftime('%H:%M:%S')
            config = comm.get_scan_config(key)
            try:
                interval = max(60.0, float(config.get("interval_seconds", 3600)))
            except (TypeError, ValueError):
                interval = 3600.0
            enabled = bool(config.get("enabled", True))
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
