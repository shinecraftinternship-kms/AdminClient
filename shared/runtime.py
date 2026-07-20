import os
import sys
from pathlib import Path


APP_NAME = "SystemScannerPro"


def is_frozen():
    return getattr(sys, "frozen", False)


def get_app_data_dir():
    if is_frozen():
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
        data_dir = os.path.join(base, APP_NAME)
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "admin", "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_resources_dir():
    if is_frozen():
        return sys._MEIPASS
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "admin")


def get_client_data_dir():
    if is_frozen():
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
        data_dir = os.path.join(base, APP_NAME, "client")
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "client")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir