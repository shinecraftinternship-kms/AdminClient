import os
from django.apps import AppConfig

IS_VERCEL = os.getenv("VERCEL", "0") == "1"


class IntelligenceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "AdminClient.admin.intelligence" if IS_VERCEL else "intelligence"
    label = "intelligence"
    verbose_name = "Intelligence - Alerts, Reports, Notifications & Audit"
