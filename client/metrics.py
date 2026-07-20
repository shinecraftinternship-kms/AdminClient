"""System metrics collection using stdlib and platform commands."""
import os
import sys
import subprocess
import socket
import time


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


def _run_command(cmd, timeout=10):
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_cpu_usage():
    """Get CPU usage percentage."""
    if sys.platform == "win32":
        raw = _run_powershell(
            "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"
        )
        try:
            return float(raw)
        except (ValueError, TypeError):
            return 0.0
    elif sys.platform == "linux":
        raw = _run_command(["grep", "-m1", "cpu ", "/proc/stat"])
        if raw:
            parts = raw.split()
            if len(parts) >= 5:
                try:
                    idle = int(parts[4])
                    total = sum(int(x) for x in parts[1:5])
                    return max(0.0, min(100.0, (1.0 - idle / max(total, 1)) * 100))
                except (ValueError, IndexError):
                    pass
    elif sys.platform == "darwin":
        raw = _run_command(["sysctl", "-n", "hw.cpu"])
    return 0.0


def get_ram_usage():
    """Returns (usage_pct, used_gb, total_gb)."""
    if sys.platform == "win32":
        raw = _run_powershell(
            "$os = Get-CimInstance Win32_OperatingSystem; "
            "$total = [math]::Round($os.TotalVisibleMemorySize/1MB, 2); "
            "$free = [math]::Round($os.FreePhysicalMemory/1MB, 2); "
            "$used = [math]::Round($total - $free, 2); "
            "Write-Output \"$used|$total\""
        )
        try:
            parts = raw.split("|")
            used = float(parts[0])
            total = float(parts[1])
            pct = (used / total * 100) if total > 0 else 0
            return pct, used, total
        except (ValueError, IndexError):
            pass
    elif sys.platform == "linux":
        info = {}
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        info[key] = int(val)
            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            total_gb = total_kb / 1048576
            used_gb = (total_kb - avail_kb) / 1048576
            pct = ((total_kb - avail_kb) / total_kb * 100) if total_kb > 0 else 0
            return pct, used_gb, total_gb
        except Exception:
            pass
    return 0.0, 0.0, 0.0


def get_disk_usage(path=None):
    """Returns (usage_pct, free_gb, total_gb)."""
    if sys.platform == "win32":
        target = path or "C:"
        raw = _run_powershell(
            f"$d = Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='{target}'\"; "
            f"$free = [math]::Round($d.FreeSpace/1GB, 2); "
            f"$total = [math]::Round($d.Size/1GB, 2); "
            f"Write-Output \"$free|$total\""
        )
        try:
            parts = raw.split("|")
            free = float(parts[0])
            total = float(parts[1])
            used = total - free
            pct = (used / total * 100) if total > 0 else 0
            return pct, free, total
        except (ValueError, IndexError):
            pass
    elif sys.platform == "linux":
        try:
            st = os.statvfs(path or "/")
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - free
            total_gb = total / (1024 ** 3)
            free_gb = free / (1024 ** 3)
            pct = (used / total * 100) if total > 0 else 0
            return pct, free_gb, total_gb
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            st = os.statvfs(path or "/")
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - free
            total_gb = total / (1024 ** 3)
            free_gb = free / (1024 ** 3)
            pct = (used / total * 100) if total > 0 else 0
            return pct, free_gb, total_gb
        except Exception:
            pass
    return 0.0, 0.0, 0.0


def get_uptime():
    """Returns uptime in seconds."""
    if sys.platform == "win32":
        raw = _run_powershell(
            "(Get-CimInstance Win32_OS).LastBootUpTime"
        )
        try:
            from datetime import datetime
            boot_time = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return int((datetime.now(boot_time.tzinfo) - boot_time).total_seconds())
        except Exception:
            pass
    elif sys.platform == "linux":
        try:
            with open("/proc/uptime") as f:
                return int(float(f.read().split()[0]))
        except Exception:
            pass
    return 0


def get_network_connected():
    """Quick check if network is reachable."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except (socket.timeout, OSError):
        pass
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3)
        return True
    except (socket.timeout, OSError):
        pass
    return False


def collect_metrics():
    """Collect all metrics in one call."""
    cpu = get_cpu_usage()
    ram_pct, ram_used, ram_total = get_ram_usage()
    disk_pct, disk_free, disk_total = get_disk_usage()
    return {
        "cpu_usage_pct": round(cpu, 1),
        "ram_usage_pct": round(ram_pct, 1),
        "disk_usage_pct": round(disk_pct, 1),
        "disk_free_gb": round(disk_free, 2),
        "disk_total_gb": round(disk_total, 2),
        "network_connected": get_network_connected(),
        "uptime_seconds": get_uptime(),
    }
