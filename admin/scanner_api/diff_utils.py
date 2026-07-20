SKIP_FIELDS = {"hostname", "platform", "platform_version", "scan_timestamp", "registration_key"}


def _val_str(v):
    if v is None:
        return "None"
    s = str(v)
    return s[:80] + "..." if len(s) > 80 else s


def _dict_diff(old, new, path=""):
    changes = []
    keys = set(list(old.keys()) + list(new.keys())) - SKIP_FIELDS
    for k in sorted(keys):
        p = f"{path}.{k}" if path else k
        ov = old.get(k)
        nv = new.get(k)
        if ov == nv:
            continue
        if isinstance(ov, dict) and isinstance(nv, dict):
            changes.extend(_dict_diff(ov, nv, p))
        elif isinstance(ov, list) and isinstance(nv, list):
            sub = _list_diff(ov, nv, p)
            changes.extend(sub)
        else:
            changes.append(f"{p}: {_val_str(ov)} \u2192 {_val_str(nv)}")
    return changes


def _list_diff(old, new, path=""):
    changes = []
    try:
        old_keys = [_item_key(o) for o in old]
        new_keys = [_item_key(n) for n in new]
    except Exception:
        if len(old) != len(new):
            changes.append(f"{path}: {len(old)} items \u2192 {len(new)} items")
        return changes

    old_by_key = {_item_key(o): o for o in old}
    new_by_key = {_item_key(n): n for n in new}

    added = [n for n in new if _item_key(n) not in old_by_key]
    removed = [o for o in old if _item_key(o) not in new_by_key]

    for item in added:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model") or item.get("kb") or _item_key(item)
        else:
            name = str(item)
        changes.append(f"+ {path}: {name} (added)")
    for item in removed:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model") or item.get("kb") or _item_key(item)
        else:
            name = str(item)
        changes.append(f"\u2212 {path}: {name} (removed)")

    for k in set(old_by_key.keys()) & set(new_by_key.keys()):
        ov = old_by_key[k]
        nv = new_by_key[k]
        if ov != nv:
            if isinstance(ov, dict) and isinstance(nv, dict):
                sub = _dict_diff(ov, nv, f"{path}[{k}]")
                changes.extend(sub)
            elif ov != nv:
                changes.append(f"{path}[{k}]: {_val_str(ov)} \u2192 {_val_str(nv)}")
    return changes


def _item_key(item):
    if isinstance(item, dict):
        for field in ("name", "model", "serial", "kb", "device", "mac", "sid"):
            if field in item and item[field]:
                return str(item[field])
        return str(sorted(item.items()))
    return str(item)


def _category_name(key):
    names = {
        "processor": "CPU",
        "ram": "RAM",
        "storage": "Storage",
        "motherboard": "Motherboard",
        "os_info": "OS",
        "network": "Network",
        "gpu": "GPU",
        "accounts": "User Accounts",
        "software": "Software",
        "updates": "Windows Updates",
        "peripherals": "Peripherals",
        "antivirus": "Antivirus",
    }
    return names.get(key, key.replace("_", " ").title())


def _compare_peripherals(old_per, new_per):
    changes = []
    all_cats = set(list(old_per.keys()) + list(new_per.keys()))
    for cat in sorted(all_cats):
        old_list = old_per.get(cat) or []
        new_list = new_per.get(cat) or []
        cat_label = cat.replace("_", " ").title()
        old_set = {d.get("name", "") for d in old_list if d.get("name")}
        new_set = {d.get("name", "") for d in new_list if d.get("name")}
        added = new_set - old_set
        removed = old_set - new_set
        for a in sorted(added):
            changes.append(f"+ {cat_label}: {a} (connected)")
        for r in sorted(removed):
            changes.append(f"\u2212 {cat_label}: {r} (disconnected)")
    return changes


def _compare_storage(old_s, new_s):
    changes = []
    od = old_s.get("disks") or []
    nd = new_s.get("disks") or []
    ch = _list_diff(od, nd, "Storage.Disk")
    changes.extend(ch)
    op = old_s.get("partitions") or []
    np_ = new_s.get("partitions") or []
    ch = _list_diff(op, np_, "Storage.Partition")
    changes.extend(ch)
    return changes


SECTION_COMPARATORS = {
    "peripherals": _compare_peripherals,
    "storage": _compare_storage,
}


def compute_scan_diff(old_scan, new_scan):
    if not old_scan or not new_scan:
        return []
    old_data = old_scan.get("scan_data") or {}
    new_data = new_scan.get("scan_data") or {}
    changes = []
    all_keys = set(list(old_data.keys()) + list(new_data.keys())) - SKIP_FIELDS
    for key in sorted(all_keys):
        ov = old_data.get(key)
        nv = new_data.get(key)
        cat_name = _category_name(key)
        if key in SECTION_COMPARATORS:
            sub = SECTION_COMPARATORS[key](ov or {}, nv or {})
        elif isinstance(ov, dict) and isinstance(nv, dict):
            sub = _dict_diff(ov, nv, cat_name)
        elif isinstance(ov, list) and isinstance(nv, list):
            sub = _list_diff(ov, nv, cat_name)
        else:
            if ov != nv:
                sub = [f"{cat_name}: {_val_str(ov)} \u2192 {_val_str(nv)}"]
            else:
                sub = []
        changes.extend(sub)
    changes.sort()
    return changes
