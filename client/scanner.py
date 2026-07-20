import sys
import platform
import json
import socket
import subprocess
import time
from datetime import datetime


def run_command(cmd, timeout=30, shell=False):
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            shell=shell, encoding="utf-8", errors="replace",
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1


def run_powershell(script, timeout=60):
    return run_command(["powershell", "-NoProfile", "-Command", script], timeout=timeout)


def read_file(path, default=""):
    try:
        with open(path, errors="replace") as f:
            return f.read().strip()
    except Exception:
        return default


def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def detect_platform():
    system = platform.system()
    if system == "Windows":
        return "Windows", platform.version()
    elif system == "Darwin":
        return "Darwin", platform.mac_ver()[0] or ""
    else:
        return "Linux", platform.platform()


def collect_all():
    print("  Scanning system...")
    result = {
        "hostname": get_hostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "scan_timestamp": datetime.now().isoformat(),
        "scanned_by": "admin_local",
    }

    result["processor"] = _get_processor()
    result["ram"] = _get_ram()
    result["storage"] = _get_storage()
    result["motherboard"] = _get_motherboard()
    result["os_info"] = _get_os_info()
    result["network"] = _get_network()
    result["gpu"] = _get_gpu()
    result["accounts"] = _get_accounts()
    result["software"] = _get_software()
    result["updates"] = _get_updates()
    result["peripherals"] = _get_peripherals()
    result["antivirus"] = _get_antivirus()

    return result


def _get_processor():
    p = {"manufacturer": "", "model": "", "serial": "", "cores": 0, "logical": 0, "speed_mhz": 0, "architecture": ""}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_Processor | Select-Object Manufacturer,Name,ProcessorId,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,Architecture | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if items:
                    item = items[0] if isinstance(items, list) else items
                    p["manufacturer"] = item.get("Manufacturer") or ""
                    p["model"] = (item.get("Name") or "").strip()
                    p["serial"] = item.get("ProcessorId") or ""
                    p["cores"] = item.get("NumberOfCores") or 0
                    p["logical"] = item.get("NumberOfLogicalProcessors") or 0
                    p["speed_mhz"] = item.get("MaxClockSpeed") or 0
                    arch_map = {0: "x86", 9: "x64", 5: "ARM", 12: "ARM64"}
                    p["architecture"] = arch_map.get(item.get("Architecture"), str(item.get("Architecture", "")))
        elif sys.platform == "linux":
            cpuinfo = read_file("/proc/cpuinfo")
            for line in cpuinfo.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k == "model name":
                        p["model"] = v
                    elif k == "vendor_id":
                        p["manufacturer"] = v
                    elif k == "cpu cores":
                        p["cores"] = int(v) if v.isdigit() else 0
                    elif k == "siblings":
                        p["logical"] = int(v) if v.isdigit() else 0
                    elif k == "cpu mhz":
                        try:
                            p["speed_mhz"] = int(float(v))
                        except ValueError:
                            pass
            stdout, _ , _ = run_command(["uname", "-m"])
            p["architecture"] = stdout.strip()
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
            p["model"] = stdout.strip()
            stdout, _, _ = run_command(["sysctl", "-n", "machdep.cpu.vendor"])
            p["manufacturer"] = stdout.strip()
            stdout, _, _ = run_command(["sysctl", "-n", "hw.logicalcpu"])
            p["logical"] = int(stdout.strip()) if stdout.strip().isdigit() else 0
            stdout, _, _ = run_command(["sysctl", "-n", "hw.physicalcpu"])
            p["cores"] = int(stdout.strip()) if stdout.strip().isdigit() else 0
            stdout, _, _ = run_command(["uname", "-m"])
            p["architecture"] = stdout.strip()
    except Exception as e:
        p["_error"] = str(e)
    return p


def _get_ram():
    r = {"manufacturer": "", "capacity_gb": "", "serial": "", "frequency_mhz": 0, "slot": ""}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,Capacity,Speed,SerialNumber,DeviceLocator | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if items:
                    item = items[0] if isinstance(items, list) else items
                    r["manufacturer"] = item.get("Manufacturer") or ""
                    cap = item.get("Capacity", 0)
                    if cap:
                        cap_gb = cap / (1024**3) if isinstance(cap, (int, float)) and cap > 1000 else float(cap)
                        r["capacity_gb"] = f"{cap_gb:.2f} GB"
                    r["serial"] = item.get("SerialNumber") or ""
                    r["frequency_mhz"] = item.get("Speed") or 0
                    r["slot"] = item.get("DeviceLocator") or ""
        elif sys.platform == "linux":
            meminfo = read_file("/proc/meminfo")
            for line in meminfo.splitlines():
                if "MemTotal" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            kb = int(parts[1])
                            r["capacity_gb"] = f"{kb / (1024**2):.2f} GB"
                        except ValueError:
                            pass
            stdout, _, _ = run_command(
                "dmidecode -t memory 2>/dev/null | grep -E 'Manufacturer:|Speed:|Serial Number:|Part Number:|Locator:' | head -10",
                shell=True, timeout=15,
            )
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k == "Manufacturer" and not r["manufacturer"]:
                        r["manufacturer"] = v
                    if k == "Speed" and not r["frequency_mhz"]:
                        try:
                            r["frequency_mhz"] = int(v.replace("MHz", "").strip())
                        except ValueError:
                            pass
                    if k == "Serial Number" and not r["serial"]:
                        r["serial"] = v
                    if k == "Locator" and not r["slot"]:
                        r["slot"] = v
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["system_profiler", "SPMemoryDataType"], timeout=30)
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if "Size" in k:
                        r["capacity_gb"] = v
                    elif "Speed" in k:
                        try:
                            r["frequency_mhz"] = int(v.replace("MHz", "").strip())
                        except ValueError:
                            pass
                    elif "Serial Number" in k:
                        r["serial"] = v
    except Exception as e:
        r["_error"] = str(e)
    return r


def _get_storage():
    disks = []
    partitions = []
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_DiskDrive | Select-Object Model,SerialNumber,Size,MediaType | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    d = {"model": item.get("Model", ""), "serial": item.get("SerialNumber", ""), "size_gb": 0.0}
                    size = item.get("Size")
                    if size:
                        try:
                            d["size_gb"] = round(int(size) / (1024**3), 2)
                        except (ValueError, TypeError):
                            pass
                    disks.append(d)
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,FileSystem,FreeSpace,Size | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    p = {"device": item.get("DeviceID", ""), "filesystem": item.get("FileSystem", ""), "free_gb": 0.0, "total_gb": 0.0}
                    free = item.get("FreeSpace")
                    total = item.get("Size")
                    if free:
                        try:
                            p["free_gb"] = round(int(free) / (1024**3), 2)
                        except (ValueError, TypeError):
                            pass
                    if total:
                        try:
                            p["total_gb"] = round(int(total) / (1024**3), 2)
                        except (ValueError, TypeError):
                            pass
                    partitions.append(p)
        elif sys.platform == "linux":
            stdout, _, _ = run_command("lsblk -d -o NAME,MODEL,SERIAL,SIZE 2>/dev/null | tail -n +2", shell=True, timeout=15)
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    d = {"model": parts[1], "serial": parts[2], "size_gb": _parse_size(parts[3])}
                    disks.append(d)
            stdout, _, _ = run_command("df -B1 --output=source,target,fstype,avail,size 2>/dev/null | tail -n +2", shell=True, timeout=15)
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    p = {"device": parts[0], "mount": parts[1], "filesystem": parts[2]}
                    try:
                        p["free_gb"] = round(int(parts[3]) / (1024**3), 2)
                        p["total_gb"] = round(int(parts[4]) / (1024**3), 2)
                    except ValueError:
                        pass
                    partitions.append(p)
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["system_profiler", "SPStorageDataType"], timeout=30)
            current = {}
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if "Volume Name" in k:
                        current["name"] = v
                    elif k == "File System":
                        current["fs"] = v
                    elif k == "Mount Point" and current:
                        d = {"model": current.get("name", ""), "size_gb": 0.0}
                        disks.append(d)
                        current = {}
    except Exception as e:
        print(f"  [WARN] Storage scan failed: {e}")
        return {"disks": disks, "partitions": partitions, "_error": str(e)}
    return {"disks": disks, "partitions": partitions}


def _parse_size(s):
    try:
        s = s.strip()
        if s.endswith("TB"):
            return round(float(s.replace("TB", "").strip()) * 1024, 2)
        elif s.endswith("GB"):
            return float(s.replace("GB", "").strip())
        elif s.endswith("MB"):
            return round(float(s.replace("MB", "").strip()) / 1024, 2)
        return float(s) / (1024**3) if s.isdigit() else 0.0
    except ValueError:
        return 0.0


def _get_motherboard():
    mb = {"manufacturer": "", "product": "", "serial": "", "version": "", "bios_vendor": "", "bios_version": ""}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,SerialNumber,Version | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                item = json.loads(stdout)
                if isinstance(item, list):
                    item = item[0] if item else {}
                mb["manufacturer"] = item.get("Manufacturer") or ""
                mb["product"] = item.get("Product") or ""
                mb["serial"] = item.get("SerialNumber") or ""
                mb["version"] = item.get("Version") or ""
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                item = json.loads(stdout)
                if isinstance(item, list):
                    item = item[0] if item else {}
                mb["bios_vendor"] = item.get("Manufacturer") or ""
                mb["bios_version"] = item.get("SMBIOSBIOSVersion") or ""
        elif sys.platform == "linux":
            mb["manufacturer"] = read_file("/sys/class/dmi/id/board_vendor")
            mb["product"] = read_file("/sys/class/dmi/id/board_name")
            mb["serial"] = read_file("/sys/class/dmi/id/board_serial")
            mb["bios_vendor"] = read_file("/sys/class/dmi/id/bios_vendor")
            mb["bios_version"] = read_file("/sys/class/dmi/id/bios_version")
        elif sys.platform == "darwin":
            mb["manufacturer"] = "Apple"
            stdout, _, _ = run_command(["system_profiler", "SPHardwareDataType"], timeout=30)
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if "Model Identifier" in k:
                        mb["product"] = v
                    elif "Boot ROM Version" in k:
                        mb["bios_version"] = v
    except Exception as e:
        print(f"  [WARN] Motherboard scan failed: {e}")
        mb["_error"] = str(e)
    return mb


def _get_os_info():
    info = {"system_type": "", "version": "", "build": "", "architecture": "", "hostname": get_hostname(), "user_accounts": []}
    try:
        if sys.platform == "win32":
            info["system_type"] = "Windows"
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                item = json.loads(stdout)
                if isinstance(item, list):
                    item = item[0] if item else {}
                info["version"] = item.get("Caption") or ""
                info["build"] = item.get("Version") or ""
                info["architecture"] = item.get("OSArchitecture") or ""
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_UserAccount | Select-Object Name | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                info["user_accounts"] = [u.get("Name", "") for u in items if isinstance(items, list)]
        elif sys.platform == "linux":
            info["system_type"] = "Linux"
            osr = read_file("/etc/os-release")
            for line in osr.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip('"')
                    if k == "PRETTY_NAME":
                        info["version"] = v
            stdout, _, _ = run_command(["uname", "-r"])
            info["build"] = stdout.strip()
            stdout, _, _ = run_command(["uname", "-m"])
            info["architecture"] = stdout.strip()
        elif sys.platform == "darwin":
            info["system_type"] = "Darwin"
            stdout, _, _ = run_command(["sw_vers"])
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    v = v.strip()
                    if k == "ProductVersion":
                        info["version"] = v
            stdout, _, _ = run_command(["uname", "-m"])
            info["architecture"] = stdout.strip()
    except Exception as e:
        print(f"  [WARN] OS info scan failed: {e}")
        info["_error"] = str(e)
    return info


def _get_network():
    net = {"interfaces": [], "public_ip": "", "private_ips": []}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } | Select-Object Description,IPAddress,MacAddress | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    ips = item.get("IPAddress") or []
                    if isinstance(ips, str):
                        ips = [ips]
                    ipv4 = [ip for ip in ips if ":" not in ip]
                    if ipv4:
                        net["private_ips"].append(ipv4[0])
                    net["interfaces"].append({
                        "name": item.get("Description", ""),
                        "mac": item.get("MacAddress", ""),
                        "ipv4": ipv4,
                    })
        elif sys.platform == "linux":
            stdout, _, _ = run_command("ip -4 -o addr show 2>/dev/null", shell=True, timeout=15)
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    iface = parts[1]
                    ip = parts[3].split("/")[0]
                    if iface != "lo":
                        net["private_ips"].append(ip)
                        net["interfaces"].append({"name": iface, "ipv4": [ip]})
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["ifconfig"], timeout=15)
            current = ""
            for line in stdout.splitlines():
                if line and not line.startswith("\t"):
                    current = line.split(":")[0]
                elif "inet " in line and current and current != "lo0":
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "inet" and i + 1 < len(parts):
                            ip = parts[i + 1]
                            net["private_ips"].append(ip)
                            net["interfaces"].append({"name": current, "ipv4": [ip]})
    except Exception as e:
        print(f"  [WARN] Network scan failed: {e}")
        net["_error"] = str(e)
    return net


def _get_gpu():
    gpus = []
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,VideoProcessor,AdapterRAM | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    g = {"name": item.get("Name", ""), "driver": item.get("DriverVersion", ""), "vram_mb": 0}
                    ram = item.get("AdapterRAM")
                    if ram:
                        try:
                            g["vram_mb"] = int(ram) // (1024**2)
                        except (ValueError, TypeError):
                            pass
                    gpus.append(g)
        elif sys.platform == "linux":
            stdout, _, _ = run_command("lspci 2>/dev/null | grep -i 'vga\\|3d\\|display'", shell=True, timeout=10)
            for line in stdout.splitlines():
                gpus.append({"name": line.strip()})
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["system_profiler", "SPDisplaysDataType"], timeout=30)
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    if k.strip() == "Chipset Model":
                        gpus.append({"name": v.strip()})
    except Exception as e:
        print(f"  [WARN] GPU scan failed: {e}")
    return gpus


def _get_accounts():
    accounts = []
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_UserAccount | Select-Object Name,Disabled,SID | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    accounts.append({
                        "name": item.get("Name", ""),
                        "disabled": item.get("Disabled", False),
                        "sid": item.get("SID", ""),
                    })
    except Exception as e:
        print(f"  [WARN] Accounts scan failed: {e}")
    return accounts


def _get_software():
    sw = []
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* 2>$null | Select-Object DisplayName,DisplayVersion,Publisher | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    name = item.get("DisplayName") or ""
                    if name:
                        sw.append({"name": name, "version": item.get("DisplayVersion", "") or "", "publisher": item.get("Publisher") or ""})
    except Exception as e:
        print(f"  [WARN] Software scan failed: {e}")
    return sw


def _get_updates():
    updates = []
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_QuickFixEngineering | Select-Object HotFixID,Description | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    updates.append({"kb": item.get("HotFixID", "") or "", "description": item.get("Description", "") or ""})
    except Exception as e:
        print(f"  [WARN] Windows updates scan failed: {e}")
    return updates


def _get_peripherals():
    per = {"keyboard": [], "mouse": [], "audio": [], "webcam": [], "printers": [], "storage": [], "other_usb": []}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_PnPEntity | Select-Object Name,Description,Manufacturer,DeviceID,Status,ClassGuid,PNPClass,Service | ConvertTo-Json -Depth 3"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    name = (item.get("Name") or "").strip()
                    if not name:
                        continue
                    desc = item.get("Description") or ""
                    mfr = item.get("Manufacturer") or ""
                    devid = item.get("DeviceID") or ""
                    status = item.get("Status") or ""
                    guid = (item.get("ClassGuid") or "").lower()
                    pnp = (item.get("PNPClass") or "").lower()
                    is_usb = "usb" in devid.lower() or pnp == "usb"
                    entry = {"name": name, "manufacturer": mfr, "description": desc, "status": status, "usb": is_usb}
                    nl = name.lower()
                    if pnp == "keyboard" or "keyboard" in guid or "keyboard" in nl:
                        per["keyboard"].append(entry)
                    elif pnp == "mouse" or ("mouse" in guid and "keyboard" not in guid) or "mouse" in nl:
                        per["mouse"].append(entry)
                    elif pnp in ("image", "camera") or "camera" in guid or "camera" in nl:
                        per["webcam"].append(entry)
                    elif pnp in ("media", "audioendpoint") or "audio" in guid or "media" in guid or "audio" in nl:
                        per["audio"].append(entry)
                    elif pnp == "printer" or "print" in nl or "printer" in devid.lower():
                        per["printers"].append(entry)
                    elif is_usb and pnp not in ("usb", "system", "computer", "hdc", "diskdrive"):
                        per["other_usb"].append(entry)
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_DiskDrive | Where-Object {$_.InterfaceType -eq 'USB'} | Select-Object Model,Manufacturer,SerialNumber,Size | ConvertTo-Json -Depth 3"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    name = (item.get("Model") or "USB Storage Device").strip()
                    mfr = item.get("Manufacturer") or ""
                    serial = item.get("SerialNumber") or ""
                    size = item.get("Size") or 0
                    size_gb = 0.0
                    if size:
                        try:
                            size_gb = round(int(size) / (1024**3), 2)
                        except (ValueError, TypeError):
                            pass
                    per["storage"].append({"name": name, "manufacturer": mfr.strip(), "serial": serial.strip(), "size_gb": size_gb, "usb": True, "status": "OK"})
        elif sys.platform == "linux":
            stdout, _, _ = run_command("lsusb 2>/dev/null", shell=True, timeout=15)
            for line in stdout.splitlines():
                parts = line.strip().split(None, 6)
                if len(parts) >= 6:
                    desc = parts[6].strip() if len(parts) > 6 else ""
                    per["other_usb"].append({"name": desc, "manufacturer": "", "description": "", "status": "connected", "usb": True})
            stdout, _, _ = run_command("lsblk -d -o NAME,MODEL,SERIAL,SIZE,TRAN 2>/dev/null | grep -i usb", shell=True, timeout=10)
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    per["storage"].append({"name": parts[1] if len(parts) > 1 else "USB Drive", "manufacturer": "", "serial": parts[2] if len(parts) > 2 else "", "size_gb": _parse_size(parts[3] if len(parts) > 3 else "0"), "usb": True, "status": "OK"})
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["system_profiler", "SPUSBDataType"], timeout=30)
            for line in stdout.splitlines():
                s = line.strip()
                if s.startswith("Product:"):
                    name = s.split(":", 1)[1].strip() if ":" in s else ""
                    per["other_usb"].append({"name": name, "manufacturer": "", "description": "", "status": "connected", "usb": True})
                elif s.startswith("Manufacturer:") and per["other_usb"]:
                    per["other_usb"][-1]["manufacturer"] = s.split(":", 1)[1].strip() if ":" in s else ""
    except Exception as e:
        print(f"  [WARN] Peripherals scan failed: {e}")
        per["_error"] = str(e)
    return per


def _get_antivirus():
    av = {"products": []}
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance -Namespace root/SecurityCenter2 AntiVirusProduct 2>$null | Select-Object displayName | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                for item in items if isinstance(items, list) else [items]:
                    av["products"].append({"name": item.get("displayName", "") or ""})
    except Exception as e:
        print(f"  [WARN] Antivirus scan failed: {e}")
        av["_error"] = str(e)
    return av
