"""Health scoring engine for the Monitoring module."""


def calculate_health_score(heartbeat_data: dict, sw_data: list = None) -> tuple:
    """Calculate composite health score from latest data.

    Returns (score: int 0-100, level: str).
    """
    cpu = heartbeat_data.get("cpu_usage_pct", 0)
    ram = heartbeat_data.get("ram_usage_pct", 0)
    disk = heartbeat_data.get("disk_usage_pct", 0)
    network = heartbeat_data.get("network_connected", True)

    cpu_pts = _cpu_score(cpu) * 0.25
    ram_pts = _ram_score(ram) * 0.25
    disk_pts = _disk_score(disk) * 0.20
    conn_pts = _connectivity_score(network) * 0.15
    sw_pts = _software_health(sw_data) * 0.15

    raw = cpu_pts + ram_pts + disk_pts + conn_pts + sw_pts
    score = max(0, min(100, round(raw)))
    level = determine_health_level(score)
    return score, level


def _cpu_score(cpu_pct: float) -> float:
    if cpu_pct <= 70:
        return 100.0
    if cpu_pct <= 85:
        return 100.0 - ((cpu_pct - 70) / 15) * 50.0
    return max(10.0, 50.0 - ((cpu_pct - 85) / 15) * 40.0)


def _ram_score(ram_pct: float) -> float:
    if ram_pct <= 70:
        return 100.0
    if ram_pct <= 85:
        return 100.0 - ((ram_pct - 70) / 15) * 50.0
    return max(10.0, 50.0 - ((ram_pct - 85) / 15) * 40.0)


def _disk_score(disk_pct: float) -> float:
    if disk_pct <= 80:
        return 100.0
    if disk_pct <= 95:
        return 100.0 - ((disk_pct - 80) / 15) * 70.0
    return max(0.0, 30.0 - ((disk_pct - 95) / 5) * 30.0)


def _connectivity_score(network_connected: bool) -> float:
    return 100.0 if network_connected else 0.0


def _software_health(sw_data: list) -> float:
    if not sw_data:
        return 80.0

    av_names = ["windows security", "defender", "antivirus", "mcafee",
                "norton", "kaspersky", "bitdefender", "avast", "avg",
                "eset", "sophos", "crowdstrike", "sentinel"]

    has_av = False
    for sw in sw_data:
        name = (sw.get("name", "") if isinstance(sw, dict) else str(sw)).lower()
        if any(av in name for av in av_names):
            has_av = True
            break

    if has_av:
        return 100.0
    return 60.0


def determine_health_level(score: int) -> str:
    if score >= 80:
        return "healthy"
    if score >= 50:
        return "warning"
    return "critical"
