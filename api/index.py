import os
import sys
import types

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if ADMIN_DIR not in sys.path:
    sys.path.insert(0, ADMIN_DIR)

PARENT_DIR = os.path.dirname(PROJECT_ROOT)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


def _make_package(name, path):
    """Create a package module with __path__ and __package__ for relative imports."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = [path]
    mod.__package__ = name
    mod.__file__ = os.path.join(path, "__init__.py")
    sys.modules[name] = mod
    return mod


_make_package("AdminClient", PROJECT_ROOT)
_make_package("AdminClient.admin", ADMIN_DIR)

for sub in sorted(os.listdir(ADMIN_DIR)):
    sub_path = os.path.join(ADMIN_DIR, sub)
    if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, "__init__.py")):
        _make_package(f"AdminClient.admin.{sub}", sub_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

from django.core.wsgi import get_wsgi_application
from mangum import Mangum

application = get_wsgi_application()
handler = Mangum(application)
