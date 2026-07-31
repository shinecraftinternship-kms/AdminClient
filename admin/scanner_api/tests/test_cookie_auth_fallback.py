import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.core.signing import TimestampSigner

from scanner_api.middleware import CookieAuthMiddleware


class CookieAuthFallbackTests(TestCase):
    def test_authenticates_user_from_signed_cookie(self):
        User = get_user_model()
        user = User.objects.create_user(username="cookie-user", password="secret123")
        signer = TimestampSigner(salt="scanner-auth-cookie")
        payload = signer.sign(json.dumps({"user_id": user.pk, "username": user.username}))

        request = RequestFactory().get("/")
        request.COOKIES = {"scanner_auth": payload}
        request.session = SessionStore()
        request.user = AnonymousUser()

        def get_response(_request):
            return None

        middleware = CookieAuthMiddleware(get_response)
        middleware(request)

        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.pk, user.pk)

    def test_restores_user_after_authentication_middleware(self):
        User = get_user_model()
        user = User.objects.create_user(username="cookie-user-2", password="secret123")
        signer = TimestampSigner(salt="scanner-auth-cookie")
        payload = signer.sign(json.dumps({"user_id": user.pk, "username": user.username}))

        request = RequestFactory().get("/")
        request.COOKIES = {"scanner_auth": payload}
        request.user = AnonymousUser()

        SessionMiddleware(lambda req: HttpResponse())(request)
        AuthenticationMiddleware(lambda req: HttpResponse())(request)

        def get_response(_request):
            return HttpResponse()

        middleware = CookieAuthMiddleware(get_response)
        response = middleware(request)

        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.pk, user.pk)
        self.assertEqual(response.status_code, 200)
