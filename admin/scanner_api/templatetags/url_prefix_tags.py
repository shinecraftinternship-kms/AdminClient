from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def prefixed_url(context, path=""):
    prefix = context.get("url_prefix", "") or ""
    clean_path = str(path or "").strip()
    if not clean_path:
        return "/" if not prefix else f"/{prefix.strip('/')}/"

    if clean_path.startswith("/"):
        clean_path = clean_path[1:]
    if not prefix:
        return f"/{clean_path}"
    return f"/{prefix.strip('/')}/{clean_path}"
