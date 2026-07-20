import os, sys, subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")
PARENT_DIR = os.path.dirname(PROJECT_ROOT)

os.environ["PYTHONPATH"] = f"{ADMIN_DIR}:{PROJECT_ROOT}:{PARENT_DIR}"

admin_client_link = os.path.join(PARENT_DIR, "AdminClient")
if not os.path.exists(admin_client_link):
    try:
        os.symlink(PROJECT_ROOT, admin_client_link)
    except OSError:
        os.makedirs(admin_client_link, exist_ok=True)

sys.exit(subprocess.call([sys.executable, os.path.join(ADMIN_DIR, "manage.py"), "collectstatic", "--noinput"]))
