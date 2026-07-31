import os
import shutil
import sys
from pathlib import Path


APP_NAME = "SystemScannerPro"


def is_frozen():
    return getattr(sys, "frozen", False)


def get_data_dir(data_dir_override=None, legacy_data_dir=None):
    if data_dir_override:
        data_dir = str(Path(data_dir_override))
    else:
        env_data_dir = os.environ.get("SCANNER_DATA_DIR")
        if env_data_dir:
            data_dir = env_data_dir
        elif sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            data_dir = os.path.join(base, APP_NAME)
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
            data_dir = os.path.join(base, APP_NAME)
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
            data_dir = os.path.join(base, APP_NAME)

    data_dir_path = Path(data_dir)
    data_dir_path.mkdir(parents=True, exist_ok=True)

    if legacy_data_dir is None:
        legacy_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    legacy_db_path = Path(legacy_data_dir) / "scanner.db"
    current_db_path = data_dir_path / "scanner.db"
    if not current_db_path.exists() and legacy_db_path.exists():
        shutil.copy2(legacy_db_path, current_db_path)

    return str(data_dir_path)


def get_app_data_dir():
    return get_data_dir()


def get_resources_dir():
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))
