import os
import logging
from django.apps import AppConfig

IS_VERCEL = os.getenv("VERCEL", "0") == "1"
logger = logging.getLogger("monitoring")


class MonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "monitoring"
    label = "monitoring"
    verbose_name = "Inventory & Monitoring"

    def ready(self):
        if IS_VERCEL:
            logger.info("Vercel mode: skipping scheduler and event bus init")
            return

        try:
            from . import subscribers  # noqa: F401 — registers event bus subscribers
            logger.info("Event bus subscribers loaded")
        except Exception as e:
            logger.warning("Could not load event bus subscribers: %s", e)

        try:
            from .scheduler import start_scheduler
            start_scheduler()
            logger.info("Monitoring scheduler started")
        except Exception as e:
            logger.warning("Could not start scheduler: %s", e)
