import os
import sys
import shutil
import subprocess
import tempfile
import hashlib
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(ROOT_DIR, "client")
ENTRY = os.path.join(CLIENT_DIR, "main.py")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_NAME = "client_scanner.exe"
DATA_DIR = os.path.join(ROOT_DIR, "admin", "data")
VERSION_FILE = os.path.join(CLIENT_DIR, "version-info.txt")
MANIFEST_FILE = os.path.join(CLIENT_DIR, "client_scanner.exe.manifest")


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
    datas = []
    for dirpath, dirnames, filenames in os.walk(CLIENT_DIR):
        for f in filenames:
            if f.endswith((".json", ".txt")):
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
        print("[INFO] To sign, set CODE_SIGN_PFX and CODE_SIGN_PASSWORD environment variables.")
        return False

    if not shutil.which("signtool"):
        print("[INFO] signtool.exe not found in PATH. Skipping code signing.")
        print("[INFO] Install Windows SDK or add signtool to PATH.")
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


def verify_binary(output_path):
    """Print SHA-256 hash for verification."""
    sha256 = hashlib.sha256()
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    print(f"  SHA-256 : {file_hash}")
    return file_hash


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

    root_init, root_created = ensure_adminclient_init()
    client_init, client_created = ensure_client_init()

    datas = collect_datas()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", OUTPUT_NAME.replace(".exe", ""),
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--noconfirm",
        "--clean",
        f"--paths={ROOT_DIR}",
        "--hidden-import=websockets",
        "--hidden-import=watchdog",
        "--hidden-import=watchdog.observers",
        "--hidden-import=watchdog.events",
        "--hidden-import=AdminClient.client.runtime",
        "--hidden-import=AdminClient.client.key_manager",
        "--hidden-import=AdminClient.client.config",
        "--hidden-import=AdminClient.client.communicator",
        "--hidden-import=AdminClient.client.scanner",
        "--hidden-import=AdminClient.client.discovery",
        "--hidden-import=AdminClient.client.metrics",
        "--hidden-import=AdminClient.client.events",
        "--hidden-import=AdminClient.client.events.dispatcher",
        "--hidden-import=AdminClient.client.events.usb_monitor",
        "--hidden-import=AdminClient.client.events.file_monitor",
        "--hidden-import=AdminClient.client.events.process_monitor",
        "--hidden-import=AdminClient.client.events.software_monitor",
        "--console",
    ]

    if os.path.exists(VERSION_FILE):
        cmd.append(f"--version-file={VERSION_FILE}")
        print(f"[INFO] Version info  : {VERSION_FILE}")
    else:
        print("[WARN] Version info file not found. Exe will have no metadata.")

    if os.path.exists(MANIFEST_FILE):
        cmd.append(f"--manifest={MANIFEST_FILE}")
        print(f"[INFO] Manifest      : {MANIFEST_FILE}")
    else:
        print("[WARN] Manifest file not found. Exe will use default manifest.")

    for src, dst in datas:
        cmd.extend(["--add-data", f"{src};{dst}"])

    cmd.append(ENTRY)

    print(f"[INFO] Entry point : {ENTRY}")
    print(f"[INFO] Output dir  : {DIST_DIR}")
    print(f"[INFO] Building with PyInstaller...")
    print()

    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            print("[ERROR] Build failed!")
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Build failed: {e}")
        sys.exit(1)

    output_path = os.path.join(DIST_DIR, OUTPUT_NAME)
    if not os.path.exists(output_path):
        exe_name = OUTPUT_NAME.replace(".exe", "")
        for f in os.listdir(DIST_DIR):
            if f.startswith(exe_name):
                output_path = os.path.join(DIST_DIR, f)
                break

    if os.path.exists(output_path):
        sign_exe(output_path)

        os.makedirs(DATA_DIR, exist_ok=True)
        dest = os.path.join(DATA_DIR, OUTPUT_NAME)
        shutil.copy2(output_path, dest)
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print()
        print("=" * 55)
        print(f"  Build successful!")
        print(f"  Output : {dest}")
        print(f"  Size   : {size_mb:.1f} MB")
        verify_binary(output_path)
        print("=" * 55)
    else:
        print(f"[ERROR] Output exe not found at {output_path}")
        sys.exit(1)

    if root_created and os.path.exists(root_init):
        try:
            os.remove(root_init)
        except OSError:
            pass

    build_cache = os.path.join(ROOT_DIR, "build")
    spec_file = os.path.join(ROOT_DIR, f"{OUTPUT_NAME.replace('.exe', '')}.spec")
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
        except OSError:
            pass


if __name__ == "__main__":
    build()
