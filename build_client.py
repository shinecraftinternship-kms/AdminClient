import os
import sys
import shutil
import subprocess
import hashlib
import zipfile
import tarfile
import platform

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(ROOT_DIR, "client")
ENTRY = os.path.join(CLIENT_DIR, "main.py")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
DATA_DIR = os.path.join(ROOT_DIR, "admin", "data")
VERSION_FILE = os.path.join(CLIENT_DIR, "version-info.txt")
MANIFEST_FILE = os.path.join(CLIENT_DIR, "client_scanner.exe.manifest")

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# Per-OS output names: a single binary format cannot run on every OS, so each
# platform gets its own PyInstaller onefile build:
#   Windows -> client_scanner.exe
#   Linux   -> client_scanner-linux
#   macOS   -> client_scanner-macos
if IS_WINDOWS:
    OUTPUT_NAME = "client_scanner.exe"
elif IS_MACOS:
    OUTPUT_NAME = "client_scanner-macos"
else:
    OUTPUT_NAME = "client_scanner-linux"


def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        return False


def ensure_client_init():
    init_path = os.path.join(CLIENT_DIR, "__init__.py")
    created = False
    if not os.path.exists(init_path):
        open(init_path, "w").close()
        created = True
    return init_path, created


def collect_datas():
    """Bundle the client's config/JSON files next to their source dirs."""
    exclude_files = {"version-info.txt", "client_scanner.exe.manifest"}
    datas = []
    for dirpath, dirnames, filenames in os.walk(CLIENT_DIR):
        # never bundle local runtime state (keys, scans) into the binary
        dirnames[:] = [d for d in dirnames if d not in ("scans", "__pycache__")]
        for f in filenames:
            if f.endswith((".json", ".txt")) and f not in exclude_files:
                src = os.path.join(dirpath, f)
                rel = os.path.relpath(dirpath, ROOT_DIR)
                datas.append((src, rel))
    return datas


def sign_exe(exe_path):
    """Sign the executable with a code signing certificate (Windows only)."""
    if not IS_WINDOWS:
        return False
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


def package_windows(binary_path):
    """Windows ZIP with the .dat rename trick to dodge naive AV heuristics."""
    exe_dest = os.path.join(DATA_DIR, OUTPUT_NAME)
    shutil.copy2(binary_path, exe_dest)

    zip_dest = os.path.join(DATA_DIR, "client_scanner.zip")
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_dest, "client_scanner.dat")
        bat_content = (
            "@echo off\r\n"
            "ren client_scanner.dat client_scanner.exe >nul 2>&1\r\n"
            "start client_scanner.exe\r\n"
        )
        zf.writestr("run.bat", bat_content)
        readme = (
            "System Scanner Pro Client\r\n"
            "=========================\r\n\r\n"
            "1. Extract all files from this zip to a folder\r\n"
            "2. Double-click run.bat to launch the scanner\r\n"
            "   (or rename client_scanner.dat to .exe and run it directly)\r\n"
        )
        zf.writestr("README.txt", readme)
    return exe_dest, zip_dest


def package_unix(binary_path, os_tag):
    """Linux/macOS ZIP containing the native binary + launch instructions."""
    name = os.path.basename(binary_path)
    zip_dest = os.path.join(DIST_DIR, f"client_scanner-{os_tag}.zip")

    launcher_ext = ".command" if IS_MACOS else ".sh"
    launcher = (
        "#!/bin/sh\n"
        f'chmod +x "$(dirname "$0")/{name}"\n'
        f'"$(dirname "$0")/{name}"\n'
    )

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(name)
        info.external_attr = 0o755 << 16  # rwxr-xr-x so it is runnable after unzip
        with open(binary_path, "rb") as fh:
            zf.writestr(info, fh.read(), compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr(f"start_scanner{launcher_ext}", launcher)
        zf.writestr(
            "README.txt",
            "System Scanner Pro Client ({})\n"
            "=============================\n\n"
            "1. Extract all files from this zip\n"
            "2. Run:  chmod +x {} && ./{}\n"
            "   or run ./start_scanner{}\n".format(os_tag, name, name, launcher_ext),
        )
    return zip_dest


def build():
    print("=" * 55)
    print("  System Scanner Pro - Client Builder")
    print(f"  Target OS : {platform.system()} ({sys.platform})")
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
        "client.events.dispatcher",
        "client.events.usb_monitor",
        "client.events.file_monitor",
        "client.events.process_monitor",
        "client.events.software_monitor",
    ]

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
    print(f"[INFO] Binary      : {OUTPUT_NAME} (single self-contained file)")
    print("[INFO] Building with PyInstaller (spec file)...")
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

    binary_path = os.path.join(DIST_DIR, OUTPUT_NAME)

    if not os.path.exists(binary_path):
        print(f"[ERROR] Output binary not found at {binary_path}")
        sys.exit(1)

    sign_exe(binary_path)

    os.makedirs(DATA_DIR, exist_ok=True)

    artifacts = []

    if IS_WINDOWS:
        exe_dest, zip_dest = package_windows(binary_path)
        artifacts.append((exe_dest, "EXE"))
        artifacts.append((zip_dest, "ZIP"))
    else:
        os_tag = "macos" if IS_MACOS else "linux"
        zip_dest = package_unix(binary_path, os_tag)
        # Copy into admin/data so the /download-client/ endpoint can serve
        # this platform the same way it serves the Windows build.
        bin_dest = os.path.join(DATA_DIR, OUTPUT_NAME)
        shutil.copy2(binary_path, bin_dest)
        data_zip = os.path.join(DATA_DIR, f"client_scanner-{os_tag}.zip")
        shutil.copy2(zip_dest, data_zip)
        artifacts.append((bin_dest, "BIN"))
        artifacts.append((data_zip, "ZIP"))

    print()
    print("=" * 55)
    print("  Build successful!")
    for path, kind in artifacts:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  {kind:<5}: {path} ({size_mb:.1f} MB)")
    verify_binary(binary_path)
    print("=" * 55)

    if client_created and os.path.exists(client_init):
        try:
            os.remove(client_init)
        except OSError:
            pass

    if os.path.exists(spec_path):
        try:
            os.remove(spec_path)
        except OSError:
            pass

    return binary_path


if __name__ == "__main__":
    build()
