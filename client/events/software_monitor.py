"""Software installation and removal detection.

Periodically scans installed software and compares with previous snapshot.
Detects:
- New software installed
- Software removed
- Version changes
- Antivirus/firewall status changes
"""

import sys
import os
import time
import json
import logging
import threading
import subprocess

logger = logging.getLogger("client.events.software_monitor")


def _run_powershell(script, timeout=30):
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


def _get_software_windows():
    software = {}
    raw = _run_powershell(
        "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        "2>$null | Select-Object DisplayName,DisplayVersion,Publisher | ConvertTo-Json"
    )
    if not raw or raw in ("", "null", "[]"):
        return software
    try:
        items = json.loads(raw) if raw.startswith("[") else [json.loads(raw)]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            name = item.get("DisplayName") or ""
            if name:
                key = name.lower()
                software[key] = {
                    "name": name,
                    "version": item.get("DisplayVersion", "") or "",
                    "publisher": item.get("Publisher", "") or "",
                }
    except Exception:
        pass
    return software


def _get_software_linux():
    software = {}
    raw = _run_command(["dpkg", "-l"], timeout=15)
    for line in raw.splitlines():
        if line.startswith("ii"):
            parts = line.split()
            if len(parts) >= 3:
                name = parts[1]
                version = parts[2]
                key = name.lower()
                software[key] = {
                    "name": name,
                    "version": version,
                    "publisher": "",
                }
    return software


def _get_software_darwin():
    software = {}
    apps_dir = "/Applications"
    if os.path.isdir(apps_dir):
        for item in os.listdir(apps_dir):
            if item.endswith(".app"):
                name = item[:-4]
                key = name.lower()
                software[key] = {
                    "name": name,
                    "version": "",
                    "publisher": "",
                }
    return software


def get_software():
    """Get current installed software snapshot."""
    if sys.platform == "win32":
        return _get_software_windows()
    elif sys.platform == "linux":
        return _get_software_linux()
    elif sys.platform == "darwin":
        return _get_software_darwin()
    return {}


def _check_antivirus_status():
    """Check if antivirus is active (Windows only)."""
    if sys.platform != "win32":
        return None

    raw = _run_powershell(
        "Get-CimInstance -Namespace root/SecurityCenter2 AntiVirusProduct 2>$null | "
        "Select-Object displayName,productState | ConvertTo-Json"
    )
    if not raw or raw in ("", "null", "[]"):
        return {"installed": False, "products": []}

    try:
        items = json.loads(raw) if raw.startswith("[") else [json.loads(raw)]
        if not isinstance(items, list):
            items = [items]
        products = []
        for item in items:
            state = item.get("productState", 0)
            is_active = (state & 0x1000) == 0
            products.append({
                "name": item.get("displayName", ""),
                "active": is_active,
                "state": state,
            })
        return {"installed": len(products) > 0, "products": products}
    except Exception:
        return None


def _check_firewall_status():
    """Check if firewall is active (Windows only)."""
    if sys.platform != "win32":
        return None

    raw = _run_powershell(
        "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json"
    )
    if not raw or raw in ("", "null", "[]"):
        return None

    try:
        items = json.loads(raw) if raw.startswith("[") else [json.loads(raw)]
        if not isinstance(items, list):
            items = [items]
        profiles = []
        for item in items:
            profiles.append({
                "name": item.get("Name", ""),
                "enabled": item.get("Enabled", False),
            })
        return profiles
    except Exception:
        return None


AV_KEYWORDS = {
    "windows security", "defender", "antivirus", "mcafee",
    "norton", "kaspersky", "bitdefender", "avast", "avg",
    "eset", "sophos", "crowdstrike", "sentinel",
}


def _is_antivirus(name):
    lower = name.lower()
    return any(av in lower for av in AV_KEYWORDS)


class SoftwareMonitor:
    """Monitors installed software changes via periodic scans."""

    def __init__(self, on_event=None, poll_interval=60):
        self.on_event = on_event
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread = None
        self._known_software = {}
        self._baseline_taken = False
        self._last_av_status = None
        self._last_fw_status = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Software monitor started (poll interval: %ds)", self.poll_interval)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Software monitor stopped")

    def take_baseline(self):
        self._known_software = get_software()
        self._baseline_taken = True
        self._last_av_status = _check_antivirus_status()
        self._last_fw_status = _check_firewall_status()
        logger.info("Software baseline: %d packages", len(self._known_software))

    def _run(self):
        while not self._stop.is_set():
            try:
                current = get_software()

                if not self._baseline_taken:
                    self._known_software = current
                    self._baseline_taken = True
                    logger.info("Software baseline established: %d packages", len(current))
                else:
                    self._detect_changes(current)

                self._known_software = current
                self._check_security_status()
            except Exception as e:
                logger.error("Software monitor error: %s", e)

            self._stop.wait(self.poll_interval)

    def _detect_changes(self, current):
        prev_keys = set(self._known_software.keys())
        curr_keys = set(current.keys())

        installed_keys = curr_keys - prev_keys
        removed_keys = prev_keys - curr_keys

        for key in installed_keys:
            sw = current[key]
            event = {
                "event_type": "software_installed",
                "severity": "info",
                "event_data": {
                    "name": sw.get("name", ""),
                    "version": sw.get("version", ""),
                    "publisher": sw.get("publisher", ""),
                    "description": f"Software installed: {sw.get('name', '')} v{sw.get('version', '')}",
                    "title": "Software Installed",
                },
            }

            if _is_antivirus(sw.get("name", "")):
                event["severity"] = "info"
                event["event_data"]["is_antivirus"] = True
                event["event_data"]["description"] = f"Antivirus installed: {sw.get('name', '')}"
                event["event_data"]["title"] = "Antivirus Installed"

            if self.on_event:
                self.on_event(event)

        for key in removed_keys:
            sw = self._known_software[key]
            event = {
                "event_type": "software_removed",
                "severity": "info",
                "event_data": {
                    "name": sw.get("name", ""),
                    "version": sw.get("version", ""),
                    "description": f"Software removed: {sw.get('name', '')}",
                    "title": "Software Removed",
                },
            }

            if _is_antivirus(sw.get("name", "")):
                event["severity"] = "critical"
                event["event_data"]["is_antivirus"] = True
                event["event_data"]["description"] = f"Antivirus REMOVED: {sw.get('name', '')}"
                event["event_data"]["title"] = "Antivirus Removed - CRITICAL"

            if self.on_event:
                self.on_event(event)

        for key in installed_keys & removed_keys:
            if key in self._known_software and key in current:
                old_ver = self._known_software[key].get("version", "")
                new_ver = current[key].get("version", "")
                if old_ver and new_ver and old_ver != new_ver:
                    event = {
                        "event_type": "software_version_changed",
                        "severity": "info",
                        "event_data": {
                            "name": current[key].get("name", ""),
                            "old_version": old_ver,
                            "new_version": new_ver,
                            "description": f"Software updated: {current[key].get('name', '')} {old_ver} -> {new_ver}",
                            "title": "Software Updated",
                        },
                    }
                    if self.on_event:
                        self.on_event(event)

    def _check_security_status(self):
        av_status = _check_antivirus_status()
        if av_status and self._last_av_status:
            prev_installed = self._last_av_status.get("installed", False)
            curr_installed = av_status.get("installed", False)

            if prev_installed and not curr_installed:
                if self.on_event:
                    self.on_event({
                        "event_type": "antivirus_disabled",
                        "severity": "critical",
                        "event_data": {
                            "description": "No antivirus products detected",
                            "title": "Antivirus Disabled/Removed",
                        },
                    })

            prev_products = {p["name"].lower(): p["active"] for p in self._last_av_status.get("products", [])}
            curr_products = {p["name"].lower(): p["active"] for p in av_status.get("products", [])}
            for name, was_active in prev_products.items():
                is_active = curr_products.get(name, False)
                if was_active and not is_active:
                    if self.on_event:
                        self.on_event({
                            "event_type": "antivirus_disabled",
                            "severity": "critical",
                            "event_data": {
                                "product": name,
                                "description": f"Antivirus protection disabled: {name}",
                                "title": "Antivirus Disabled",
                            },
                        })

        self._last_av_status = av_status

        fw_status = _check_firewall_status()
        if fw_status and self._last_fw_status:
            prev_map = {p["name"]: p["enabled"] for p in self._last_fw_status}
            curr_map = {p["name"]: p["enabled"] for p in fw_status}
            for profile_name, was_enabled in prev_map.items():
                is_enabled = curr_map.get(profile_name, True)
                if was_enabled and not is_enabled:
                    if self.on_event:
                        self.on_event({
                            "event_type": "firewall_disabled",
                            "severity": "critical",
                            "event_data": {
                                "profile": profile_name,
                                "description": f"Firewall profile disabled: {profile_name}",
                                "title": "Firewall Disabled",
                            },
                        })

        self._last_fw_status = fw_status
