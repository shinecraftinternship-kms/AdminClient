from django.urls import re_path


def _agent_consumer(scope, receive, send):
    from . import consumers
    return consumers.AgentConsumer.as_asgi()(scope, receive, send)


def _dashboard_consumer(scope, receive, send):
    from . import consumers
    return consumers.DashboardConsumer.as_asgi()(scope, receive, send)


websocket_urlpatterns = [
    re_path(r"ws/agent/(?P<agent_id>[^/]+)/$", _agent_consumer),
    re_path(r"ws/dashboard/$", _dashboard_consumer),
]
