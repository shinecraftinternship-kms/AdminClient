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

if "AdminClient" not in sys.modules:
    _admin_pkg = types.ModuleType("AdminClient")
    _admin_pkg.__path__ = [PROJECT_ROOT]
    _admin_pkg.__package__ = "AdminClient"
    sys.modules["AdminClient"] = _admin_pkg

if "AdminClient.admin" not in sys.modules:
    _admin_sub = types.ModuleType("AdminClient.admin")
    _admin_sub.__path__ = [ADMIN_DIR]
    _admin_sub.__package__ = "AdminClient.admin"
    sys.modules["AdminClient.admin"] = _admin_sub
    sys.modules["AdminClient"].admin = _admin_sub

for sub in os.listdir(ADMIN_DIR):
    sub_path = os.path.join(ADMIN_DIR, sub)
    if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, "__init__.py")):
        mod_name = f"AdminClient.admin.{sub}"
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            mod.__path__ = [sub_path]
            mod.__package__ = mod_name
            sys.modules[mod_name] = mod
            setattr(sys.modules["AdminClient.admin"], sub, mod)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

from django.core.wsgi import get_wsgi_application
from mangum import Mangum

application = get_wsgi_application()
handler = Mangum(application)
