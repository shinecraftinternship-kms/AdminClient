"""USB device insertion and removal detection.

Platform-specific implementations:
- Windows: WMI Win32_PnPEntity polling
- Linux: udevadm monitoring
- macOS: IOKit/System_profiler polling
"""

import sys
import time
import json
import logging
import threading
import subprocess

logger = logging.getLogger("client.events.usb")


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


def _get_usb_devices_windows():
    raw = _run_powershell(
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'USB' -or $_.DeviceID -like 'USB\\*' } | "
        "Select-Object DeviceID,Name,Manufacturer,PNPClass,Status | "
        "ConvertTo-Json -Compress"
    )
    devices = {}
    if not raw or raw in ("", "null"):
        return devices
    try:
        items = json.loads(raw) if raw.startswith("[") else [json.loads(raw)]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            devid = item.get("DeviceID", "")
            if devid:
                devices[devid] = {
                    "name": item.get("Name", ""),
                    "manufacturer": item.get("Manufacturer", ""),
                    "class": item.get("PNPClass", ""),
                    "status": item.get("Status", ""),
                }
    except Exception:
        pass
    return devices


def _get_usb_devices_linux():
    devices = {}
    raw = _run_command(["lsusb"])
    for i, line in enumerate(raw.splitlines()):
        parts = line.strip().split(None, 5)
        if len(parts) >= 6:
            bus = parts[1]
            dev = parts[3].rstrip(":")
            desc = parts[5]
            key = f"usb-{bus}-{dev}"
            devices[key] = {
                "name": desc,
                "bus": bus,
                "device": dev,
                "status": "connected",
            }
    return devices


def _get_usb_devices_darwin():
    devices = {}
    raw = _run_command(["system_profiler", "SPUSBDataType"], timeout=30)
    current_name = ""
    current_key = ""
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("Product:") or s.startswith("Manufacturer:"):
            continue
        if ":" in s and not s.startswith("\t"):
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k == "Product ID" or k == "Vendor ID":
                continue
            if v and not current_key:
                current_name = v
                current_key = f"usb-{v}"
                devices[current_key] = {"name": v, "status": "connected"}
    return devices


def get_usb_devices():
    """Get current USB device snapshot."""
    if sys.platform == "win32":
        return _get_usb_devices_windows()
    elif sys.platform == "linux":
        return _get_usb_devices_linux()
    elif sys.platform == "darwin":
        return _get_usb_devices_darwin()
    return {}


class USBMonitor:
    """Monitors USB device insertion and removal.

    Runs in a background thread, polling for USB device changes
    at a configurable interval.
    """

    def __init__(self, on_event=None, poll_interval=5):
        self.on_event = on_event
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread = None
        self._known_devices = {}
        self._baseline_taken = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("USB monitor started (poll interval: %ds)", self.poll_interval)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("USB monitor stopped")

    def take_baseline(self):
        """Capture initial USB state without generating events."""
        self._known_devices = get_usb_devices()
        self._baseline_taken = True
        logger.info("USB baseline: %d devices", len(self._known_devices))

    def _run(self):
        while not self._stop.is_set():
            try:
                current = get_usb_devices()

                if not self._baseline_taken:
                    self._known_devices = current
                    self._baseline_taken = True
                    logger.info("USB baseline established: %d devices", len(current))
                else:
                    self._detect_changes(current)

                self._known_devices = current
            except Exception as e:
                logger.error("USB monitor error: %s", e)

            self._stop.wait(self.poll_interval)

    def _detect_changes(self, current):
        prev_keys = set(self._known_devices.keys())
        curr_keys = set(current.keys())

        inserted_keys = curr_keys - prev_keys
        removed_keys = prev_keys - curr_keys

        for key in inserted_keys:
            device = current[key]
            event = {
                "event_type": "usb_inserted",
                "severity": "info",
                "event_data": {
                    "device_id": key,
                    "name": device.get("name", ""),
                    "manufacturer": device.get("manufacturer", ""),
                    "description": f"USB device connected: {device.get('name', key)}",
                    "title": "USB Device Connected",
                },
            }
            logger.info("USB inserted: %s", device.get("name", key))
            if self.on_event:
                self.on_event(event)

        for key in removed_keys:
            device = self._known_devices[key]
            event = {
                "event_type": "usb_removed",
                "severity": "info",
                "event_data": {
                    "device_id": key,
                    "name": device.get("name", ""),
                    "manufacturer": device.get("manufacturer", ""),
                    "description": f"USB device disconnected: {device.get('name', key)}",
                    "title": "USB Device Disconnected",
                },
            }
            logger.info("USB removed: %s", device.get("name", key))
            if self.on_event:
                self.on_event(event)

        for key in inserted_keys | removed_keys:
            if key in self._known_devices and key in current:
                old_status = self._known_devices[key].get("status", "")
                new_status = current[key].get("status", "")
                if old_status and new_status and old_status != new_status:
                    event = {
                        "event_type": "usb_status_change",
                        "severity": "warning" if new_status.lower() not in ("ok", "connected") else "info",
                        "event_data": {
                            "device_id": key,
                            "name": current[key].get("name", ""),
                            "previous_status": old_status,
                            "new_status": new_status,
                            "description": f"USB status changed: {old_status} -> {new_status}",
                            "title": "USB Status Change",
                        },
                    }
                    if self.on_event:
                        self.on_event(event)
