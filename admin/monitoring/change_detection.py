"""Enhanced change detection for hardware and software inventory."""

import hashlib
import json


HW_CHANGE_SEVERITY = {
    "motherboard": "warning",
    "cpu": "warning",
    "ram": "info",
    "storage": "critical",
    "gpu": "info",
    "network": "info",
}


def detect_hardware_changes(client, previous_hw: list, current_hw: list) -> list:
    """Compare hardware inventory snapshots.

    Returns list of change dicts with component_type, change_type,
    description, severity, previous, new.
    """
    changes = []

    prev_by_type = {}
    for entry in previous_hw:
        ct = entry.get("component_type", "")
        if ct not in prev_by_type:
            prev_by_type[ct] = []
        prev_by_type[ct].append(entry)

    curr_by_type = {}
    for entry in current_hw:
        ct = entry.get("component_type", "")
        if ct not in curr_by_type:
            curr_by_type[ct] = []
        curr_by_type[ct].append(entry)

    all_types = set(list(prev_by_type.keys()) + list(curr_by_type.keys()))

    for ct in all_types:
        prev_items = prev_by_type.get(ct, [])
        curr_items = curr_by_type.get(ct, [])

        prev_fps = {_item_fingerprint(i) for i in prev_items}
        curr_fps = {_item_fingerprint(i) for i in curr_items}

        added = [i for i in curr_items if _item_fingerprint(i) not in prev_fps]
        removed = [i for i in prev_items if _item_fingerprint(i) not in curr_fps]

        for item in removed:
            name = _item_name(item)
            severity = HW_CHANGE_SEVERITY.get(ct, "info")
            changes.append({
                "component_type": ct,
                "change_type": "removed",
                "description": f"{ct.upper()} removed: {name}",
                "severity": severity,
                "previous": item,
                "new": {},
            })

        for item in added:
            name = _item_name(item)
            severity = HW_CHANGE_SEVERITY.get(ct, "info")
            changes.append({
                "component_type": ct,
                "change_type": "added",
                "description": f"{ct.upper()} added: {name}",
                "severity": severity,
                "previous": {},
                "new": item,
            })

        matched_prev = [i for i in prev_items if _item_fingerprint(i) in curr_fps]
        matched_curr = [i for i in curr_items if _item_fingerprint(i) in prev_fps]
        for pi, ci in zip(
            sorted(matched_prev, key=_item_fingerprint),
            sorted(matched_curr, key=_item_fingerprint),
        ):
            if pi != ci:
                diff = _shallow_diff(pi, ci)
                if diff:
                    changes.append({
                        "component_type": ct,
                        "change_type": "modified",
                        "description": f"{ct.upper()} modified: {diff}",
                        "severity": "info",
                        "previous": pi,
                        "new": ci,
                    })

    return changes


def detect_software_changes(client, previous_sw: list, current_sw: list,
                            unauthorized_list: list = None) -> list:
    """Compare software inventories.

    Returns structured change objects for new, removed, version-changed,
    unauthorized software.
    """
    changes = []
    unauthorized = [s.lower() for s in (unauthorized_list or [])]

    prev_map = {}
    for sw in previous_sw:
        name = (sw.get("name", "") if isinstance(sw, dict) else str(sw)).lower()
        prev_map[name] = sw

    curr_map = {}
    for sw in current_sw:
        name = (sw.get("name", "") if isinstance(sw, dict) else str(sw)).lower()
        curr_map[name] = sw

    for name, sw in curr_map.items():
        if name not in prev_map:
            changes.append({
                "component_type": "software",
                "change_type": "added",
                "description": f"Software installed: {sw.get('name', name)}",
                "severity": "info",
                "previous": {},
                "new": sw,
            })
            if name in unauthorized:
                changes.append({
                    "component_type": "software",
                    "change_type": "unauthorized",
                    "description": f"Unauthorized software detected: {sw.get('name', name)}",
                    "severity": "warning",
                    "previous": {},
                    "new": sw,
                })

    for name, sw in prev_map.items():
        if name not in curr_map:
            changes.append({
                "component_type": "software",
                "change_type": "removed",
                "description": f"Software removed: {sw.get('name', name)}",
                "severity": "info",
                "previous": sw,
                "new": {},
            })
            av_names = ["windows security", "defender", "antivirus", "mcafee",
                        "norton", "kaspersky", "bitdefender"]
            if any(av in name for av in av_names):
                changes.append({
                    "component_type": "software",
                    "change_type": "antivirus_removed",
                    "description": f"Antivirus software removed: {sw.get('name', name)}",
                    "severity": "critical",
                    "previous": sw,
                    "new": {},
                })

    for name in curr_map:
        if name in prev_map:
            old_ver = prev_map[name].get("version", "")
            new_ver = curr_map[name].get("version", "")
            if old_ver and new_ver and old_ver != new_ver:
                changes.append({
                    "component_type": "software",
                    "change_type": "version_changed",
                    "description": f"Software updated: {curr_map[name].get('name', name)} {old_ver} → {new_ver}",
                    "severity": "info",
                    "previous": prev_map[name],
                    "new": curr_map[name],
                })

    return changes


def detect_antivirus_status(prev_sw: list, curr_sw: list) -> list:
    """Detect AV disabled, removed, or changed."""
    changes = []
    av_names = ["windows security", "defender", "antivirus", "mcafee",
                "norton", "kaspersky", "bitdefender", "avast", "avg",
                "eset", "sophos", "crowdstrike", "sentinel"]

    prev_av = []
    curr_av = []
    for sw in prev_sw:
        name = (sw.get("name", "") if isinstance(sw, dict) else str(sw)).lower()
        if any(av in name for av in av_names):
            prev_av.append(sw)
    for sw in curr_sw:
        name = (sw.get("name", "") if isinstance(sw, dict) else str(sw)).lower()
        if any(av in name for av in av_names):
            curr_av.append(sw)

    if prev_av and not curr_av:
        changes.append({
            "component_type": "software",
            "change_type": "antivirus_removed",
            "description": "Antivirus software is no longer detected",
            "severity": "critical",
            "previous": prev_av[0],
            "new": {},
        })

    return changes


def component_fingerprint(component_data: dict) -> str:
    """Generate a stable fingerprint for a hardware component."""
    return _item_fingerprint(component_data)


def _item_fingerprint(item: dict) -> str:
    """Generate fingerprint from component data dict."""
    if not isinstance(item, dict):
        return hashlib.md5(str(item).encode()).hexdigest()[:16]

    data = item.get("component_data", item)
    key_fields = ["serial", "model", "name", "manufacturer", "product", "serialnumber"]
    parts = []
    for f in key_fields:
        val = data.get(f, "")
        if val:
            parts.append(str(val))

    if not parts:
        parts = [json.dumps(data, sort_keys=True, default=str)]

    combined = "||".join(parts)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def _item_name(item: dict) -> str:
    data = item.get("component_data", item)
    for f in ["name", "model", "product", "manufacturer"]:
        if data.get(f):
            return str(data[f])
    return "Unknown"


def _shallow_diff(a: dict, b: dict) -> str:
    diffs = []
    all_keys = set(list(a.keys()) + list(b.keys()))
    skip = {"component_type", "fingerprint", "scan_id", "created_at"}
    for k in sorted(all_keys - skip):
        if k in ("component_data",):
            continue
        av = a.get(k)
        bv = b.get(k)
        if av != bv:
            diffs.append(f"{k}: {av} → {bv}")
    return "; ".join(diffs) if diffs else ""
