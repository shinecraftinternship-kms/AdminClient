from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase

from scanner_api import middleware, templates


class AuthRedirectTests(SimpleTestCase):
    def test_prefixes_internal_next_paths(self):
        self.assertEqual(
            templates.normalize_next_url("/executive-dashboard/", "user-company"),
            "/user-company/executive-dashboard/",
        )

    def test_prefixes_settings_route_for_company_urls(self):
        self.assertEqual(templates.normalize_next_url("/settings/", "user-company"), "/user-company/setting/")

    def test_falls_back_to_prefixed_dashboard_when_next_is_empty(self):
        self.assertEqual(templates.normalize_next_url("", "user-company"), "/user-company/")

    def test_redirects_login_pages_to_prefixed_dashboard(self):
        self.assertEqual(templates.normalize_next_url("/login/", "user-company"), "/user-company/")

    def test_build_url_prefix_path_handles_empty_and_prefixed_values(self):
        self.assertEqual(middleware.build_url_prefix_path(""), "/")
        self.assertEqual(middleware.build_url_prefix_path("user-company"), "/user-company/")

    def test_login_redirect_uses_next_value_without_crashing(self):
        factory = RequestFactory()
        request = factory.post(
            "/login/",
            {"identifier": "asdf", "password": "asdf@123", "next": "/executive-dashboard/"},
        )
        request.user = SimpleNamespace(is_authenticated=False)
        SessionMiddleware(lambda req: None).process_request(request)

        user = SimpleNamespace(pk=1, username="asdf", is_active=True)
        profile = SimpleNamespace(company=None)

        def save(*args, **kwargs):
            return None

        profile.save = save

        with patch("scanner_api.templates.authenticate", return_value=user), \
            patch("scanner_api.auth_utils.check_account_lock", return_value=(False, 0)), \
            patch("scanner_api.auth_utils.record_login_attempt"), \
            patch("scanner_api.auth_utils.log_audit_event"), \
            patch("scanner_api.auth_utils.create_login_history", return_value=SimpleNamespace(id=77)), \
            patch("scanner_api.auth_utils.get_client_ip", return_value="127.0.0.1"), \
            patch("scanner_api.validators.validate_email", return_value=False), \
            patch("scanner_api.templates.login"), \
            patch("scanner_api.models.ActivityLog.objects.create"), \
            patch("scanner_api.models.AdministratorProfile.objects.get_or_create", return_value=(profile, True)), \
            patch("scanner_api.models.Company.objects.get_or_create", return_value=(SimpleNamespace(slug="acme", name="Acme"), True)):
            response = templates.login_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/asdf-acme/executive-dashboard/")
