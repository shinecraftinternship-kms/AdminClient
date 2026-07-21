#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import types


def _setup_admin_client():
    admin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(admin_dir)
    parent_dir = os.path.dirname(project_root)

    if admin_dir not in sys.path:
        sys.path.insert(0, admin_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    if "AdminClient" not in sys.modules:
        pkg = types.ModuleType("AdminClient")
        pkg.__path__ = [project_root]
        pkg.__package__ = "AdminClient"
        sys.modules["AdminClient"] = pkg

    if "AdminClient.admin" not in sys.modules:
        sub = types.ModuleType("AdminClient.admin")
        sub.__path__ = [admin_dir]
        sub.__package__ = "AdminClient.admin"
        sys.modules["AdminClient.admin"] = sub
        sys.modules["AdminClient"].admin = sub

    for name in os.listdir(admin_dir):
        d = os.path.join(admin_dir, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "__init__.py")):
            mod_name = f"AdminClient.admin.{name}"
            if mod_name not in sys.modules:
                mod = types.ModuleType(mod_name)
                mod.__path__ = [d]
                mod.__package__ = mod_name
                sys.modules[mod_name] = mod
                setattr(sys.modules["AdminClient.admin"], name, mod)


_setup_admin_client()


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
