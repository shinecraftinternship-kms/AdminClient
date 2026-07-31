from django.test import SimpleTestCase

from scanner_api import templates


class AuthRedirectTests(SimpleTestCase):
    def test_preserves_internal_next_paths(self):
        self.assertEqual(
            templates.normalize_next_url("/asdf-asdff/executive-dashboard/", "user-company"),
            "/asdf-asdff/executive-dashboard/",
        )

    def test_falls_back_to_prefixed_dashboard_when_next_is_empty(self):
        self.assertEqual(templates.normalize_next_url("", "user-company"), "/user-company/")

    def test_redirects_login_pages_to_prefixed_dashboard(self):
        self.assertEqual(templates.normalize_next_url("/login/", "user-company"), "/user-company/")
