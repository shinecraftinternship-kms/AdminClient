import os
import sys
import shutil
import subprocess
import hashlib
import zipfile

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(ROOT_DIR, "client")
ENTRY = os.path.join(CLIENT_DIR, "main.py")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_NAME = "client_scanner.exe"
DATA_DIR = os.path.join(ROOT_DIR, "admin", "data")
VERSION_FILE = os.path.join(CLIENT_DIR, "version-info.txt")
MANIFEST_FILE = os.path.join(CLIENT_DIR, "client_scanner.exe.manifest")
ZIP_NAME = "client_scanner.zip"


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def ensure_adminclient_init():
    init_path = os.path.join(ROOT_DIR, "__init__.py")
    created = False
    if not os.path.exists(init_path):
        open(init_path, "w").close()
        created = True
    return init_path, created


def ensure_client_init():
    init_path = os.path.join(CLIENT_DIR, "__init__.py")
    created = False
    if not os.path.exists(init_path):
        open(init_path, "w").close()
        created = True
    return init_path, created


def collect_datas():
    exclude_files = {"version-info.txt", "client_scanner.exe.manifest"}
    datas = []
    for dirpath, dirnames, filenames in os.walk(CLIENT_DIR):
        for f in filenames:
            if f.endswith((".json", ".txt")) and f not in exclude_files:
                src = os.path.join(dirpath, f)
                rel = os.path.relpath(dirpath, ROOT_DIR)
                datas.append((src, rel))
    return datas


def sign_exe(exe_path):
    """Sign the executable with a code signing certificate."""
    pfx_path = os.environ.get("CODE_SIGN_PFX", "")
    pfx_password = os.environ.get("CODE_SIGN_PASSWORD", "")
    timestamp_url = os.environ.get("CODE_SIGN_TIMESTAMP", "http://timestamp.digicert.com")

    if not pfx_path or not os.path.exists(pfx_path):
        print("[INFO] No CODE_SIGN_PFX set or file not found. Skipping code signing.")
        return False

    if not shutil.which("signtool"):
        print("[INFO] signtool.exe not found in PATH. Skipping code signing.")
        return False

    print(f"[INFO] Signing executable with certificate: {pfx_path}")
    cmd = [
        "signtool", "sign",
        "/f", pfx_path,
        "/fd", "sha256",
        "/tr", timestamp_url,
        "/td", "sha256",
        "/d", "System Scanner Pro Client Agent",
    ]
    if pfx_password:
        cmd.extend(["/p", pfx_password])
    cmd.append(exe_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("[INFO] Code signing successful!")
            return True
        else:
            print(f"[WARN] Code signing failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[WARN] Code signing error: {e}")
        return False


def verify_binary(file_path):
    """Print SHA-256 hash for verification."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    print(f"  SHA-256 : {file_hash}")
    return file_hash


def create_zip(folder_path, zip_path):
    """Create a ZIP archive from a folder."""
    print(f"[INFO] Creating ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                zf.write(file_path, arcname)


def build():
    print("=" * 55)
    print("  System Scanner Pro - Client Builder")
    print("=" * 55)
    print()

    if not os.path.exists(ENTRY):
        print(f"[ERROR] Entry point not found: {ENTRY}")
        sys.exit(1)

    if not check_pyinstaller():
        print("[INFO] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    client_init, client_created = ensure_client_init()

    datas = collect_datas()

    hiddenimports = [
        "websockets",
        "watchdog",
        "watchdog.observers",
        "watchdog.events",
        "client.runtime",
        "client.key_manager",
        "client.config",
        "client.communicator",
        "client.scanner",
        "client.discovery",
        "client.metrics",
        "client.fingerprint",
        "client.events",
        "client.events.dispatcher",
        "client.events.usb_monitor",
        "client.events.file_monitor",
        "client.events.process_monitor",
        "client.events.software_monitor",
    ]

    # Use a spec file instead of a giant command line: 300+ --add-data
    # entries with long absolute paths blow past the Windows 32k cmdline
    # limit (WinError 206). The spec has no such limit.
    spec_content = f"""\
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    [{ENTRY!r}],
    pathex=[{CLIENT_DIR!r}],
    binaries=[],
    datas={datas!r},
    hiddenimports={hiddenimports!r},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name={OUTPUT_NAME.replace('.exe', '')!r},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

    spec_path = os.path.join(ROOT_DIR, "client_scanner.spec")
    with open(spec_path, "w", encoding="utf-8") as fh:
        fh.write(spec_content)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--noconfirm",
        "--clean",
        spec_path,
    ]

    print(f"[INFO] Entry point : {ENTRY}")
    print(f"[INFO] Output dir  : {DIST_DIR}")
    print(f"[INFO] Mode        : onefile (single self-contained exe)")
    print(f"[INFO] Building with PyInstaller (spec file)...")
    print()

    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            print("[ERROR] Build failed!")
            print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
            print(result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Build failed: {e}")
        sys.exit(1)

    exe_path = os.path.join(DIST_DIR, OUTPUT_NAME)

    if not os.path.exists(exe_path):
        print(f"[ERROR] Output exe not found at {exe_path}")
        sys.exit(1)

    sign_exe(exe_path)

    os.makedirs(DATA_DIR, exist_ok=True)

    exe_dest = os.path.join(DATA_DIR, OUTPUT_NAME)
    shutil.copy2(exe_path, exe_dest)
    print(f"[INFO] Copied exe to: {exe_dest}")

    zip_dest = os.path.join(DATA_DIR, ZIP_NAME)
    print(f"[INFO] Creating ZIP: {zip_dest}")
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_dest, "client_scanner.dat")
        bat_content = '@echo off\r\nren client_scanner.dat client_scanner.exe >nul 2>&1\r\nstart client_scanner.exe\r\n'
        zf.writestr("run.bat", bat_content)
        readme = (
            "System Scanner Pro Client\r\n"
            "=========================\r\n\r\n"
            "1. Extract all files from this zip to a folder\r\n"
            "2. Double-click run.bat to launch the scanner\r\n"
            "   (or rename client_scanner.dat to .exe and run it directly)\r\n"
        )
        zf.writestr("README.txt", readme)

    exe_size_mb = os.path.getsize(exe_dest) / (1024 * 1024)
    zip_size_mb = os.path.getsize(zip_dest) / (1024 * 1024)
    print()
    print("=" * 55)
    print(f"  Build successful!")
    print(f"  EXE    : {exe_dest} ({exe_size_mb:.1f} MB)")
    print(f"  ZIP    : {zip_dest} ({zip_size_mb:.1f} MB)")
    verify_binary(exe_dest)
    print("=" * 55)

    if client_created and os.path.exists(client_init):
        try:
            os.remove(client_init)
        except OSError:
            pass

    spec_file = os.path.join(ROOT_DIR, "client_scanner.spec")
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
        except OSError:
            pass


if __name__ == "__main__":
    build()
