import os
import sys
import types
import ctypes
import ctypes.util
import traceback

_log = []

DB_HOST = os.getenv("DB_HOST", "")
POOLER_HOST = os.getenv("POOLER_HOST", "aws-0-us-east-1.pooler.supabase.com")


def _patch_c_getaddrinfo():
    if not DB_HOST:
        return
    try:
        libc_name = ctypes.util.find_library("c")
        if not libc_name:
            return
        libc = ctypes.CDLL(libc_name)

        original = libc.getaddrinfo
        original.restype = ctypes.c_int

        AddrInfo = ctypes.c_void_p
        AddrHints = ctypes.c_void_p

        CBType = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            AddrHints,
            ctypes.POINTER(AddrInfo),
        )

        db_host_enc = DB_HOST.encode("utf-8")
        pooler_enc = POOLER_HOST.encode("utf-8")

        def hook(node, service, hints, res):
            try:
                hostname = node.decode("utf-8") if node else ""
            except Exception:
                hostname = ""
            if hostname == db_host_enc.decode("utf-8") or node == db_host_enc:
                return original(pooler_enc, service, hints, res)
            return original(node, service, hints, res)

        libc.getaddrinfo = CBType(hook)
        _log.append(f"DNS_PATCH: redirected {DB_HOST} -> {POOLER_HOST}")
    except Exception as e:
        _log.append(f"DNS_PATCH_FAILED: {e}")


_patch_c_getaddrinfo()


def _diag(environ, start_response):
    body = "\n".join(_log).encode()
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def _init():
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")

    for p in [PROJECT_ROOT, ADMIN_DIR, os.path.dirname(PROJECT_ROOT)]:
        if p not in sys.path:
            sys.path.insert(0, p)

    def _make_package(name, path):
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
    os.environ.setdefault("SCANNER_DATA_DIR", "/tmp")

    import django
    django.setup()

    from django.core.handlers.wsgi import WSGIHandler
    return WSGIHandler()


try:
    _real_app = _init()
except Exception:
    _log.append("INIT_CRASH: " + traceback.format_exc())
    _real_app = None


def application(environ, start_response):
    if environ.get("PATH_INFO", "") == "/__diag":
        return _diag(environ, start_response)
    if _real_app is None:
        return _diag(environ, start_response)
    try:
        return _real_app(environ, start_response)
    except Exception:
        _log.append("REQ_CRASH: " + traceback.format_exc())
        return _diag(environ, start_response)
