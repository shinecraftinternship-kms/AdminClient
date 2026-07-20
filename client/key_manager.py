import sys
import json
import os
import random
import string
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from AdminClient.client.runtime import is_frozen, get_client_data_dir

CLIENT_DATA_DIR = get_client_data_dir()
KEY_FILE = os.path.join(CLIENT_DATA_DIR, "client_key.json")
CONFIG_FILE = os.path.join(CLIENT_DATA_DIR, "client_config.json")


def generate_key(length=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _load_key_data():
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_key_data(data):
    with open(KEY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_or_create_key():
    data = _load_key_data()
    if data.get("registration_key"):
        return data["registration_key"]
    key = generate_key()
    data["registration_key"] = key
    _save_key_data(data)
    return key


def save_key(key):
    data = _load_key_data()
    data["registration_key"] = key
    _save_key_data(data)


def load_or_create_fingerprint():
    from AdminClient.client.fingerprint import generate_fingerprint
    data = _load_key_data()
    fp = data.get("device_fingerprint")
    if fp:
        return fp
    fp = generate_fingerprint()
    data["device_fingerprint"] = fp
    _save_key_data(data)
    return fp


def load_config():
    defaults = {
        "admin_url": "http://localhost:80",
        "scan_interval": 3600,
        "auto_start": True,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
