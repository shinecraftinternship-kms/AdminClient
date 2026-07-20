import os
from django.apps import AppConfig

IS_VERCEL = os.getenv("VERCEL", "0") == "1"


class MaintenanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "AdminClient.admin.maintenance" if IS_VERCEL else "maintenance"
    label = "maintenance"
    verbose_name = "Maintenance & License Management"
