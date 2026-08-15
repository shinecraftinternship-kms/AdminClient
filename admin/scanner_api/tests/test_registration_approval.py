import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

import django
from django.test import RequestFactory, TestCase


django.setup()

from django.contrib.auth import get_user_model

from scanner_api.models import Client
from scanner_api.views import RegisterClientView, ApproveClientView

User = get_user_model()


class RegistrationApprovalTests(TestCase):
    def test_same_device_re_registration_does_not_keep_old_approval_when_auto_approve_is_off(self):
        Client.objects.create(
            registration_key="old-key",
            hostname="Old Host",
            platform="Linux",
            device_fingerprint="fp-123",
            approved=True,
            status="online",
        )

        factory = RequestFactory()
        request = factory.post(
            "/api/register",
            {
                "registration_key": "new-key",
                "hostname": "New Host",
                "platform": "Linux",
                "client_version": "2.0",
                "device_fingerprint": "fp-123",
            },
            content_type="application/json",
        )

        response = RegisterClientView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertFalse(response.data["auto_approved"])

        client = Client.objects.get(registration_key="new-key")
        self.assertFalse(client.approved)
        self.assertEqual(client.status, "pending")

    def test_existing_key_same_device_keeps_approval(self):
        Client.objects.create(
            registration_key="KEY-1",
            hostname="Host A",
            platform="Windows",
            device_fingerprint="fp-abc",
            approved=True,
            status="online",
        )

        factory = RequestFactory()
        request = factory.post(
            "/api/register",
            {
                "registration_key": "KEY-1",
                "hostname": "Host A",
                "platform": "Windows",
                "client_version": "2.0",
                "device_fingerprint": "fp-abc",
            },
            content_type="application/json",
        )

        response = RegisterClientView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending")
        self.assertTrue(response.data["approved"])

        client = Client.objects.get(registration_key="KEY-1")
        self.assertTrue(client.approved)

    def test_existing_key_different_device_resets_approval(self):
        Client.objects.create(
            registration_key="KEY-1",
            hostname="Host A",
            platform="Windows",
            device_fingerprint="fp-abc",
            approved=True,
            status="online",
        )

        factory = RequestFactory()
        request = factory.post(
            "/api/register",
            {
                "registration_key": "KEY-1",
                "hostname": "Host B",
                "platform": "Windows",
                "client_version": "2.0",
                "device_fingerprint": "fp-def",
            },
            content_type="application/json",
        )

        response = RegisterClientView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending")
        self.assertFalse(response.data["approved"])

        client = Client.objects.get(registration_key="KEY-1")
        self.assertFalse(client.approved)
        self.assertEqual(client.status, "pending")
        self.assertEqual(client.device_fingerprint, "fp-def")

    def test_new_client_is_pending_when_auto_approve_is_off(self):
        factory = RequestFactory()
        request = factory.post(
            "/api/register",
            {
                "registration_key": "BRAND-NEW",
                "hostname": "Fresh Host",
                "platform": "Windows",
                "client_version": "2.0",
                "device_fingerprint": "fp-fresh",
            },
            content_type="application/json",
        )

        response = RegisterClientView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["auto_approved"])

        client = Client.objects.get(registration_key="BRAND-NEW")
        self.assertFalse(client.approved)
        self.assertEqual(client.status, "pending")

    def test_approving_deleted_client_reactivates_and_shows_it(self):
        admin = User.objects.create_user(username="admin", password="pass1234", is_superuser=True)
        client = Client.objects.create(
            registration_key="DELETED-KEY",
            hostname="Hidden Host",
            platform="Linux",
            deleted=True,
            approved=False,
            status="pending",
            owner=admin,
        )

        factory = RequestFactory()
        request = factory.post(
            "/api/approve",
            {"registration_key": "DELETED-KEY"},
            content_type="application/json",
        )
        request.user = admin

        response = ApproveClientView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        client.refresh_from_db()
        self.assertTrue(client.approved)
        self.assertEqual(client.status, "online")
        self.assertFalse(client.deleted)
