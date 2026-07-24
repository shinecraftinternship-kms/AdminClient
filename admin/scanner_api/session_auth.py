from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication without CSRF enforcement.

    All API views are already decorated with @csrf_exempt.
    This lets browser requests (with session cookie) be authenticated
    while keeping the client/agent endpoints unauthenticated.
    """

    def enforce_csrf(self, request):
        return
