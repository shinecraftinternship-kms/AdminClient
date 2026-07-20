"""Process monitoring via periodic snapshots and diffing.

Detects:
- New processes started
- Processes terminated
- High-CPU or suspicious processes
"""

import sys
import os
import time
import json
import logging
import threading
import subprocess

logger = logging.getLogger("client.events.process_monitor")


def _run_powershell(script, timeout=15):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _run_command(cmd, timeout=15):
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _get_processes_windows():
    processes = {}
    raw = _run_powershell(
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,ExecutablePath,ParentProcessId,CreationDate | "
        "ConvertTo-Json -Compress"
    )
    if not raw or raw in ("", "null"):
        return processes
    try:
        items = json.loads(raw) if raw.startswith("[") else [json.loads(raw)]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            pid = item.get("ProcessId")
            if pid is not None:
                name = item.get("Name", "unknown")
                key = f"{name}:{pid}"
                processes[key] = {
                    "pid": pid,
                    "name": name,
                    "path": item.get("ExecutablePath", ""),
                    "parent_pid": item.get("ParentProcessId", 0),
                    "created": item.get("CreationDate", ""),
                }
    except Exception:
        pass
    return processes


def _get_processes_linux():
    processes = {}
    try:
        pids = [d for d in os.listdir("/proc") if d.isdigit()]
        for pid_str in pids:
            try:
                with open(f"/proc/{pid_str}/comm", errors="replace") as f:
                    name = f.read().strip()
                key = f"{name}:{pid_str}"
                exe = ""
                try:
                    exe = os.readlink(f"/proc/{pid_str}/exe")
                except Exception:
                    pass
                processes[key] = {
                    "pid": int(pid_str),
                    "name": name,
                    "path": exe,
                }
            except Exception:
                continue
    except Exception:
        pass
    return processes


def _get_processes_darwin():
    processes = {}
    raw = _run_command(["ps", "-axo", "pid,comm"], timeout=10)
    for line in raw.splitlines()[1:]:
        parts = line.strip().split(None, 1)
        if len(parts) >= 2:
            pid = parts[0]
            name = parts[1]
            key = f"{name}:{pid}"
            processes[key] = {
                "pid": int(pid),
                "name": name,
                "path": "",
            }
    return processes


def get_processes():
    """Get current process snapshot."""
    if sys.platform == "win32":
        return _get_processes_windows()
    elif sys.platform == "linux":
        return _get_processes_linux()
    elif sys.platform == "darwin":
        return _get_processes_darwin()
    return {}


SUSPICIOUS_NAMES = {
    "mimikatz", "psexec", "netcat", "nc", "ncat",
    "meterpreter", "cobaltstrike", "beacon",
    "keylogger", "rat", "backdoor", "rootkit",
}

SUSPICIOUS_PATHS_KEYWORDS = {
    "\\temp\\", "\\tmp\\", "/tmp/", "/var/tmp/",
    "\\appdata\\local\\temp\\",
}


def _is_suspicious(process_data):
    name = process_data.get("name", "").lower()
    path = process_data.get("path", "").lower()

    if any(s in name for s in SUSPICIOUS_NAMES):
        return True, "known_suspicious_name"

    if any(kw in path for kw in SUSPICIOUS_PATHS_KEYWORDS):
        return True, "running_from_temp"

    return False, ""


class ProcessMonitor:
    """Monitors process creation and termination via periodic snapshots."""

    def __init__(self, on_event=None, poll_interval=10):
        self.on_event = on_event
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread = None
        self._known_processes = {}
        self._baseline_taken = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Process monitor started (poll interval: %ds)", self.poll_interval)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Process monitor stopped")

    def take_baseline(self):
        self._known_processes = get_processes()
        self._baseline_taken = True
        logger.info("Process baseline: %d processes", len(self._known_processes))

    def _run(self):
        while not self._stop.is_set():
            try:
                current = get_processes()

                if not self._baseline_taken:
                    self._known_processes = current
                    self._baseline_taken = True
                    logger.info("Process baseline established: %d processes", len(current))
                else:
                    self._detect_changes(current)

                self._known_processes = current
            except Exception as e:
                logger.error("Process monitor error: %s", e)

            self._stop.wait(self.poll_interval)

    def _detect_changes(self, current):
        prev_keys = set(self._known_processes.keys())
        curr_keys = set(current.keys())

        started_keys = curr_keys - prev_keys
        terminated_keys = prev_keys - curr_keys

        for key in started_keys:
            proc = current[key]
            suspicious, reason = _is_suspicious(proc)
            severity = "critical" if suspicious else "info"

            event = {
                "event_type": "process_started" if not suspicious else "suspicious_process",
                "severity": severity,
                "event_data": {
                    "pid": proc.get("pid", 0),
                    "name": proc.get("name", ""),
                    "path": proc.get("path", ""),
                    "description": f"Process started: {proc.get('name', '')} (PID {proc.get('pid', 0)})",
                    "title": "Suspicious Process Detected" if suspicious else "Process Started",
                },
            }
            if suspicious:
                event["event_data"]["reason"] = reason

            if self.on_event:
                self.on_event(event)

        for key in terminated_keys:
            proc = self._known_processes[key]
            event = {
                "event_type": "process_terminated",
                "severity": "info",
                "event_data": {
                    "pid": proc.get("pid", 0),
                    "name": proc.get("name", ""),
                    "description": f"Process terminated: {proc.get('name', '')} (PID {proc.get('pid', 0)})",
                    "title": "Process Terminated",
                },
            }
            if self.on_event:
                self.on_event(event)
