import os
from django.apps import AppConfig

IS_VERCEL = os.getenv("VERCEL", "0") == "1"


class ScannerApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "AdminClient.admin.scanner_api" if IS_VERCEL else "scanner_api"
    label = "scanner_api"
