import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

django.setup()

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from monitoring.routing import websocket_urlpatterns

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
except ImportError:
    application = django_asgi_app
