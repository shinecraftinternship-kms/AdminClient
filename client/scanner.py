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
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
    sticks = []
    total_gb = 0.0
    try:
        if sys.platform == "win32":
            stdout, _, _ = run_powershell(
                "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,Capacity,Speed,SerialNumber,DeviceLocator,PartNumber,ConfiguredClockSpeed | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    s = {"manufacturer": "", "capacity_gb": "", "serial": "", "frequency_mhz": 0, "slot": "", "part_number": ""}
                    s["manufacturer"] = item.get("Manufacturer") or ""
                    cap = item.get("Capacity", 0)
                    if cap:
                        try:
                            cap_gb = cap / (1024**3) if isinstance(cap, (int, float)) and cap > 1000 else float(cap)
                            s["capacity_gb"] = f"{cap_gb:.2f} GB"
                            total_gb += cap_gb
                        except (ValueError, TypeError):
                            pass
                    serial = item.get("SerialNumber") or ""
                    if serial and serial not in ("00000000", "To Be Filled By O.E.M.", "0000000000", "0000", ""):
                        s["serial"] = serial.strip()
                    s["frequency_mhz"] = item.get("ConfiguredClockSpeed") or item.get("Speed") or 0
                    s["slot"] = item.get("DeviceLocator") or ""
                    s["part_number"] = (item.get("PartNumber") or "").strip()
                    sticks.append(s)
            # Fallback 1: Get-WmiObject (older WMI, sometimes returns serial when CIM doesn't)
            if sticks and any(not s["serial"] for s in sticks):
                try:
                    stdout_wmi, _, _ = run_powershell(
                        "Get-WmiObject Win32_PhysicalMemory | Select-Object SerialNumber,PartNumber | ConvertTo-Json"
                    )
                    if stdout_wmi and stdout_wmi not in ("", "null"):
                        wmi_items = json.loads(stdout_wmi) if stdout_wmi.startswith("[") else [json.loads(stdout_wmi)]
                        if not isinstance(wmi_items, list):
                            wmi_items = [wmi_items]
                        for idx, wi in enumerate(wmi_items):
                            if idx < len(sticks):
                                wserial = wi.get("SerialNumber") or ""
                                if wserial and wserial not in ("00000000", "To Be Filled By O.E.M.", "0000", ""):
                                    sticks[idx]["serial"] = wserial.strip()
                                elif not sticks[idx]["serial"] and wi.get("PartNumber"):
                                    sticks[idx]["part_number"] = (wi["PartNumber"] or "").strip()
                except Exception:
                    pass
            # Fallback 2: wmic memorychip (legacy, different WMI path)
            if sticks and any(not s["serial"] for s in sticks):
                try:
                    stdout2, _, _ = run_command(
                        ["wmic", "memorychip", "get", "SerialNumber", "/value"],
                        timeout=10,
                    )
                    wmic_serials = []
                    for line in stdout2.splitlines():
                        if "SerialNumber=" in line:
                            val = line.split("=", 1)[1].strip()
                            if val and val not in ("00000000", "To Be Filled By O.E.M.", "0000", ""):
                                wmic_serials.append(val)
                    if wmic_serials:
                        for idx, ws in enumerate(wmic_serials):
                            if idx < len(sticks) and not sticks[idx]["serial"]:
                                sticks[idx]["serial"] = ws
                except Exception:
                    pass
            # Fallback 3: Read raw SMBIOS table via GetSystemFirmwareTable API
            # This is the key fallback for desktops/PCs where WMI doesn't expose serial
            if sticks and any(not s["serial"] for s in sticks):
                try:
                    import ctypes
                    import struct as _struct
                    kernel32 = ctypes.windll.kernel32
                    RSMB = 0x52534D42
                    buf_size = kernel32.GetSystemFirmwareTable(RSMB, 0, None, 0)
                    if buf_size > 0:
                        buf = ctypes.create_string_buffer(buf_size)
                        got = kernel32.GetSystemFirmwareTable(RSMB, 0, buf, buf_size)
                        if got > 0:
                            raw = buf.raw[:got]
                            if len(raw) >= 8:
                                major_ver = raw[1]
                                table_len = _struct.unpack_from('<I', raw, 4)[0] if major_ver >= 2 else _struct.unpack_from('<H', raw, 4)[0]
                                smbios = raw[8:8 + table_len]
                                pos = 0
                                while pos + 1 < len(smbios):
                                    rec_type = smbios[pos]
                                    rec_len = smbios[pos + 1]
                                    if rec_type == 0:
                                        break
                                    if rec_type == 17 and rec_len >= 0x16:
                                        str_idx = smbios[pos + 0x15]
                                        if str_idx > 0:
                                            str_start = pos + rec_len
                                            str_count = 0
                                            sp = str_start
                                            while sp < len(smbios):
                                                if smbios[sp] == 0:
                                                    str_count += 1
                                                    if str_count == str_idx:
                                                        sp += 1
                                                        break
                                                sp += 1
                                            if sp < len(smbios):
                                                end = smbios.index(0, sp) if 0 in smbios[sp:sp + 64] else sp + 64
                                                serial = smbios[sp:end].decode('ascii', errors='replace').strip()
                                                serial = ''.join(c for c in serial if c.isalnum() or c in '-_ ')
                                                if serial and len(serial) >= 4 and serial not in ('Not Specified', 'Not Available', 'To Be Filled By O.E.M.', '00000000', '0000000000000000', 'FFFFFFFF'):
                                                    for s in sticks:
                                                        if not s["serial"]:
                                                            s["serial"] = serial
                                                            break
                                    str_start = pos + rec_len
                                    null_count = 0
                                    sp2 = str_start
                                    while sp2 < len(smbios):
                                        if smbios[sp2] == 0:
                                            null_count += 1
                                            if null_count >= 2:
                                                pos = sp2 + 1
                                                break
                                        else:
                                            null_count = 0
                                        sp2 += 1
                                    else:
                                        break
                except Exception:
                    pass
        elif sys.platform == "linux":
            meminfo = read_file("/proc/meminfo")
            for line in meminfo.splitlines():
                if "MemTotal" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            kb = int(parts[1])
                            total_gb = kb / (1024**2)
                        except ValueError:
                            pass
            stdout, _, _ = run_command(
                "dmidecode -t memory 2>/dev/null | grep -A5 -i 'Memory Device'",
                shell=True, timeout=15,
            )
            current = {}
            for line in stdout.splitlines():
                line = line.strip()
                if not line or line == "--":
                    if current:
                        sticks.append(current)
                        current = {}
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k == "Manufacturer":
                        current["manufacturer"] = v
                    elif k == "Size" and v != "No Module Installed":
                        current["capacity_gb"] = v
                    elif k == "Speed":
                        try:
                            current["frequency_mhz"] = int(v.replace("MHz", "").strip())
                        except (ValueError, TypeError):
                            pass
                    elif k == "Serial Number":
                        current["serial"] = v if v else ""
                    elif k == "Locator":
                        current["slot"] = v
            if current and current.get("manufacturer"):
                sticks.append(current)
            if not sticks:
                s = {"manufacturer": "", "capacity_gb": f"{total_gb:.2f} GB" if total_gb else "", "serial": "", "frequency_mhz": 0, "slot": ""}
                sticks.append(s)
        elif sys.platform == "darwin":
            stdout, _, _ = run_command(["system_profiler", "SPMemoryDataType"], timeout=30)
            current = {}
            for line in stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if "Size" in k:
                        if current:
                            sticks.append(current)
                        current = {"manufacturer": "", "capacity_gb": v, "serial": "", "frequency_mhz": 0, "slot": ""}
                    elif "Speed" in k:
                        try:
                            current["frequency_mhz"] = int(v.replace("MHz", "").strip())
                        except (ValueError, TypeError):
                            pass
                    elif "Serial Number" in k:
                        current["serial"] = v
                    elif "Vendor" in k:
                        current["manufacturer"] = v
            if current and current.get("capacity_gb"):
                sticks.append(current)
    except Exception as e:
        pass

    if not sticks:
        sticks = [{"manufacturer": "", "capacity_gb": "", "serial": "", "frequency_mhz": 0, "slot": ""}]
    first = sticks[0]
    total_str = f"{total_gb:.2f} GB" if total_gb > 0 else first.get("capacity_gb", "")
    return {
        "manufacturer": first.get("manufacturer", ""),
        "capacity_gb": total_str,
        "total_capacity_gb": total_str,
        "serial": first.get("serial", ""),
        "frequency_mhz": first.get("frequency_mhz", 0),
        "slot": first.get("slot", ""),
        "part_number": first.get("part_number", ""),
        "sticks": sticks,
        "stick_count": len(sticks),
    }


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
    seen = set()

    def _add(name, version="", publisher="", source=""):
        name = (name or "").strip()
        if name and name not in seen:
            seen.add(name)
            sw.append({"name": name, "version": (version or "").strip(), "publisher": (publisher or "").strip(), "source": source})

    try:
        if sys.platform == "win32":
            # Windows Registry (classic desktop apps)
            registry_paths = [
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
            ]
            for reg_path in registry_paths:
                stdout, _, _ = run_powershell(
                    f"Get-ItemProperty '{reg_path}' 2>$null | Select-Object DisplayName,DisplayVersion,Publisher | ConvertTo-Json"
                )
                if stdout and stdout not in ("", "null", "[]"):
                    items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                    if not isinstance(items, list):
                        items = [items]
                    for item in items:
                        _add(item.get("DisplayName"), item.get("DisplayVersion"), item.get("Publisher"), "registry")

            # MS Store / UWP apps
            stdout, _, _ = run_powershell(
                "Get-AppxPackage -AllUsers 2>$null | Select-Object Name,Version,Author | ConvertTo-Json"
            )
            if stdout and stdout not in ("", "null", "[]"):
                items = json.loads(stdout) if stdout.startswith("[") else [json.loads(stdout)]
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    _add(item.get("Name"), item.get("Version"), item.get("Author"), "msstore")

            # Winget packages
            stdout, _, rc = run_command(
                ["winget", "list", "--accept-source-agreements", "--disable-interactivity"],
                timeout=60
            )
            if rc == 0 and stdout:
                lines = stdout.splitlines()
                header_idx = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith("Name") and "Id" in line and "Version" in line:
                        header_idx = i
                        break
                if header_idx >= 0:
                    separator_line = lines[header_idx + 1] if header_idx + 1 < len(lines) else ""
                    col_positions = [m.start() for m in __import__("re").finditer(r"\S", separator_line)]
                    for line in lines[header_idx + 2:]:
                        line = line.strip()
                        if not line or line.startswith("---") or line.startswith("Name"):
                            continue
                        parts = []
                        for ci in range(len(col_positions)):
                            start = col_positions[ci]
                            end = col_positions[ci + 1] if ci + 1 < len(col_positions) else len(line)
                            parts.append(line[start:end].strip())
                        if len(parts) >= 3:
                            _add(parts[0], parts[2], "", "winget")

            # npm global packages
            stdout, _, rc = run_command(["npm", "list", "-g", "--depth=0", "--json"], timeout=30)
            if rc == 0 and stdout:
                try:
                    npm_data = json.loads(stdout)
                    deps = npm_data.get("dependencies", {})
                    for pkg_name, info in deps.items():
                        if isinstance(info, dict):
                            _add(pkg_name, info.get("version", ""), "", "npm")
                except (json.JSONDecodeError, AttributeError):
                    pass

            # pip packages
            stdout, _, rc = run_command(["pip", "list", "--format=json"], timeout=30)
            if rc == 0 and stdout:
                try:
                    pip_data = json.loads(stdout)
                    if isinstance(pip_data, list):
                        for pkg in pip_data:
                            if isinstance(pkg, dict):
                                _add(pkg.get("name"), pkg.get("version"), pkg.get("author") or pkg.get("home-page", ""), "pip")
                except (json.JSONDecodeError, AttributeError):
                    pass

        elif sys.platform == "linux":
            # dpkg (Debian/Ubuntu)
            stdout, _, rc = run_command(["dpkg", "-l"], timeout=30)
            if rc == 0 and stdout:
                for line in stdout.splitlines():
                    if line.startswith("ii"):
                        parts = line.split(None, 2)
                        if len(parts) >= 3:
                            _add(parts[1], parts[2].split()[0] if parts[2] else "", "", "dpkg")

            # snap packages
            stdout, _, rc = run_command(["snap", "list"], timeout=30)
            if rc == 0 and stdout:
                lines = stdout.splitlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        _add(parts[0], parts[1] if len(parts) > 1 else "", parts[3] if len(parts) > 3 else "", "snap")

            # flatpak packages
            stdout, _, rc = run_command(
                ["flatpak", "list", "--columns=application,version,origin"], timeout=30
            )
            if rc == 0 and stdout:
                for line in stdout.splitlines()[1:]:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        _add(parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else "", "flatpak")

        elif sys.platform == "darwin":
            # /Applications/*.app bundles
            stdout, _, rc = run_command(
                ["find", "/Applications", "-maxdepth", "2", "-name", "*.app", "-type", "d"], timeout=15
            )
            if rc == 0 and stdout:
                for app_path in stdout.splitlines():
                    app_name = app_path.rsplit("/", 1)[-1].replace(".app", "")
                    _add(app_name, "", "", "macos-apps")

            # Homebrew formulae
            stdout, _, rc = run_command(["brew", "list", "--formula", "--json"], timeout=30)
            if rc == 0 and stdout:
                try:
                    brew_data = json.loads(stdout)
                    if isinstance(brew_data, list):
                        for pkg in brew_data:
                            if isinstance(pkg, dict):
                                _add(pkg.get("full_name") or pkg.get("name"), pkg.get("versions", {}).get("stable", ""), "", "brew")
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Mac App Store (mas)
            stdout, _, rc = run_command(["mas", "list"], timeout=30)
            if rc == 0 and stdout:
                for line in stdout.splitlines():
                    parts = line.split(None, 2)
                    if len(parts) >= 2:
                        name = parts[1] if len(parts) > 1 else ""
                        version = parts[2].split(" (")[0] if len(parts) > 2 else ""
                        _add(name, version, "", "mas")

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
    per = {"keyboard": [], "mouse": [], "audio": [], "webcam": [], "printers": [], "storage": [], "other_usb": [], "monitors": []}
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
            # Scan for monitors/displays using multiple methods and merge results
            try:
                def _decode_wmi_str(arr):
                    if isinstance(arr, list):
                        return "".join(chr(c) for c in arr if c != 0).strip()
                    return ""

                def _monitor_key(name, serial=""):
                    """Dedup key: prefer serial, fallback to normalised name."""
                    if serial and serial.lower() not in ("", "none"):
                        return f"sn:{serial.lower()}"
                    return f"name:{(name or '').lower().strip()}"

                seen_monitors = {}

                # Method 1: WmiMonitorID (most reliable, needs admin on some systems)
                try:
                    stdout_mon2, _, _ = run_powershell(
                        "Get-CimInstance -Namespace root\\wmi WmiMonitorID 2>$null | "
                        "Select-Object ManufacturerName,ProductCodeID,SerialNumberID,"
                        "UserFriendlyName,VideoInputType | ConvertTo-Json"
                    )
                    if stdout_mon2 and stdout_mon2 not in ("", "null", "[]"):
                        mon_items2 = json.loads(stdout_mon2) if stdout_mon2.startswith("[") else [json.loads(stdout_mon2)]
                        if not isinstance(mon_items2, list):
                            mon_items2 = [mon_items2]
                        for mon in mon_items2:
                            mfr = _decode_wmi_str(mon.get("ManufacturerName") or [])
                            model = _decode_wmi_str(mon.get("UserFriendlyName") or [])
                            serial_arr = mon.get("SerialNumberID") or []
                            serial = _decode_wmi_str(serial_arr) if isinstance(serial_arr, list) else str(serial_arr)
                            key = _monitor_key(model, serial)
                            if key not in seen_monitors:
                                seen_monitors[key] = {
                                    "name": model or "Monitor", "manufacturer": mfr,
                                    "model": model or "Monitor", "serial": serial,
                                    "status": "OK", "usb": False
                                }
                except Exception:
                    pass

                # Method 2: Win32_PnPEntity display class (works without admin)
                try:
                    stdout_pnp, _, _ = run_powershell(
                        "Get-CimInstance Win32_PnPEntity | Where-Object { "
                        "$_.PNPClass -eq 'Monitor' -or "
                        "$_.ClassGuid -eq '{4d36e96e-e325-11ce-bfc1-08002be10318}' } | "
                        "Select-Object Name,Manufacturer,DeviceID | ConvertTo-Json"
                    )
                    if stdout_pnp and stdout_pnp not in ("", "null", "[]"):
                        pnp_items = json.loads(stdout_pnp) if stdout_pnp.startswith("[") else [json.loads(stdout_pnp)]
                        if not isinstance(pnp_items, list):
                            pnp_items = [pnp_items]
                        for mon in pnp_items:
                            name = (mon.get("Name") or "Monitor").strip()
                            mfr = (mon.get("Manufacturer") or "").strip()
                            dev_id = mon.get("DeviceID") or ""
                            # Extract serial from DeviceID if available
                            serial_from_id = ""
                            if dev_id and "\\\\" in dev_id:
                                parts = dev_id.split("\\")
                                serial_from_id = parts[-1] if parts else ""
                            key = _monitor_key(name, serial_from_id)
                            if key not in seen_monitors:
                                seen_monitors[key] = {
                                    "name": name, "manufacturer": mfr, "model": name,
                                    "serial": serial_from_id, "status": "OK", "usb": False
                                }
                            elif not seen_monitors[key].get("manufacturer") and mfr:
                                seen_monitors[key]["manufacturer"] = mfr
                except Exception:
                    pass

                # Method 3: Win32_DesktopMonitor for resolution info
                try:
                    stdout_mon, _, _ = run_powershell(
                        "Get-CimInstance Win32_DesktopMonitor | "
                        "Select-Object Name,Manufacturer,ScreenWidth,ScreenHeight,PNPDeviceID | ConvertTo-Json"
                    )
                    if stdout_mon and stdout_mon not in ("", "null", "[]"):
                        mon_items = json.loads(stdout_mon) if stdout_mon.startswith("[") else [json.loads(stdout_mon)]
                        if not isinstance(mon_items, list):
                            mon_items = [mon_items]
                        for mon in mon_items:
                            name = (mon.get("Name") or "Monitor").strip()
                            mfr = (mon.get("Manufacturer") or "").strip()
                            width = mon.get("ScreenWidth") or ""
                            height = mon.get("ScreenHeight") or ""
                            resolution = f"{width}x{height}" if width and height else ""
                            pnp_id = mon.get("PNPDeviceID") or ""
                            serial_from_pnp = ""
                            if pnp_id and "\\\\" in pnp_id:
                                parts = pnp_id.split("\\")
                                serial_from_pnp = parts[-1] if parts else ""
                            key = _monitor_key(name, serial_from_pnp)
                            if key in seen_monitors:
                                if resolution:
                                    seen_monitors[key]["resolution"] = resolution
                                if not seen_monitors[key].get("manufacturer") and mfr:
                                    seen_monitors[key]["manufacturer"] = mfr
                            elif resolution:
                                seen_monitors[key] = {
                                    "name": name, "manufacturer": mfr, "model": name,
                                    "serial": serial_from_pnp, "resolution": resolution,
                                    "status": "OK", "usb": False
                                }
                except Exception:
                    pass

                # Finalise: convert dedup dict to list
                per["monitors"] = list(seen_monitors.values())
            except Exception:
                pass
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
            stdout_mon, _, _ = run_command("xrandr --listmonitors 2>/dev/null", shell=True, timeout=5)
            for line in stdout_mon.splitlines():
                parts = line.strip().split()
                if len(parts) >= 4 and parts[0].isdigit():
                    name = " ".join(parts[3:])
                    per["monitors"].append({"name": name, "manufacturer": "", "model": name, "status": "OK", "usb": False})
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
