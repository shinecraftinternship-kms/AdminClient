import hashlib
import json
import platform
import subprocess
import sys


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


def _get_motherboard_serial():
    if sys.platform == "win32":
        raw = _run_powershell(
            "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"
        )
        return raw.strip() if raw and raw.strip() else ""
    elif sys.platform == "linux":
        try:
            with open("/sys/class/dmi/id/board_serial", errors="replace") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""


def _get_cpu_id():
    if sys.platform == "win32":
        raw = _run_powershell(
            "Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty ProcessorId"
        )
        return raw.strip() if raw and raw.strip() else ""
    elif sys.platform == "linux":
        cpuinfo = ""
        try:
            with open("/proc/cpuinfo", errors="replace") as f:
                cpuinfo = f.read()
        except Exception:
            return ""
        for line in cpuinfo.splitlines():
            if line.lower().startswith("serial"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    return ""


def _get_disk_serial():
    if sys.platform == "win32":
        raw = _run_powershell(
            "Get-CimInstance Win32_DiskDrive | Select-Object -First 1 -ExpandProperty SerialNumber"
        )
        return raw.strip() if raw and raw.strip() else ""
    elif sys.platform == "linux":
        raw = _run_command(["lsblk", "-d", "-n", "-o", "SERIAL", "/dev/sda"])
        if raw:
            return raw.splitlines()[0].strip()
        raw = _run_command(["lsblk", "-d", "-n", "-o", "SERIAL", "/dev/nvme0n1"])
        if raw:
            return raw.splitlines()[0].strip()
    return ""


def _get_mac_addresses():
    if sys.platform == "win32":
        raw = _run_powershell(
            "Get-CimInstance Win32_NetworkAdapterConfiguration | "
            "Where-Object { $_.MACAddress -and $_.IPEnabled } | "
            "Select-Object -ExpandProperty MACAddress"
        )
        if raw:
            macs = sorted([m.strip() for m in raw.splitlines() if m.strip()])
            return "|".join(macs)
    elif sys.platform == "linux":
        raw = _run_command(["cat", "/sys/class/net/*/address"])
        if raw:
            macs = sorted(set(m.strip() for m in raw.splitlines() if m.strip() and m.strip() != "00:00:00:00:00:00"))
            return "|".join(macs)
    return ""


def generate_fingerprint():
    parts = [
        _get_motherboard_serial(),
        _get_cpu_id(),
        _get_disk_serial(),
        _get_mac_addresses(),
        platform.machine(),
    ]
    combined = "||".join(parts)
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
    return digest.upper()


def generate_and_describe():
    raw = {
        "motherboard": _get_motherboard_serial(),
        "cpu_id": _get_cpu_id(),
        "disk_serial": _get_disk_serial(),
        "mac_addresses": _get_mac_addresses(),
        "machine_type": platform.machine(),
    }
    fp = generate_fingerprint()
    return fp, raw
