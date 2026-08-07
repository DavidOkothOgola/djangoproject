import json
import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import TenantProfile, ChatSession, Message, MpesaTransaction


def make_consultant(username="expert1", slug="expert1", rate=500):
    user = User.objects.create_user(username=username)
    user.set_password("TestPass123!")
    user.save()
    profile = TenantProfile.objects.create(
        user=user,
        slug=slug,
        display_name="Expert One",
        hourly_rate=rate,
        subscription_status=True,
        subscription_expires_at=timezone.now() + timezone.timedelta(days=30),
    )
    return user, profile


class TenantProfileModelTests(TestCase):
    def test_subscription_is_active_true(self):
        _, profile = make_consultant()
        self.assertTrue(profile.subscription_is_active())

    def test_subscription_is_active_false_when_expired(self):
        _, profile = make_consultant()
        profile.subscription_expires_at = timezone.now() - timezone.timedelta(days=1)
        profile.save()
        self.assertFalse(profile.subscription_is_active())

    def test_subscription_is_active_false_when_not_set(self):
        _, profile = make_consultant()
        profile.subscription_status = False
        profile.save()
        self.assertFalse(profile.subscription_is_active())


class ChatRoomViewTests(TestCase):
    def setUp(self):
        _, self.profile = make_consultant()

    def test_get_enter_name_page(self):
        resp = self.client.get(f"/{self.profile.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Consultation")

    def test_post_creates_session_and_renders_chat(self):
        resp = self.client.post(f"/{self.profile.slug}/", {"display_name": "Alice"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Type a message")
        self.assertEqual(ChatSession.objects.filter(client_display_name="Alice").count(), 1)

    def test_post_without_name_shows_error(self):
        resp = self.client.post(f"/{self.profile.slug}/", {"display_name": ""})
        self.assertContains(resp, "Please enter a display name")

    def test_session_reused_on_second_visit(self):
        self.client.post(f"/{self.profile.slug}/", {"display_name": "Bob"})
        self.client.get(f"/{self.profile.slug}/")
        self.assertEqual(ChatSession.objects.filter(client_display_name="Bob").count(), 1)

    def test_inactive_consultant_shows_inactive_page(self):
        self.profile.subscription_status = False
        self.profile.save()
        resp = self.client.get(f"/{self.profile.slug}/")
        self.assertContains(resp, "Unavailable")


class MpesaCallbackTests(TestCase):
    def setUp(self):
        _, self.profile = make_consultant()
        self.session = ChatSession.objects.create(
            tenant=self.profile,
            client_display_name="Carol",
            session_token="abc123",
        )
        self.txn = MpesaTransaction.objects.create(
            tenant=self.profile,
            chat_session=self.session,
            checkout_request_id="ws_CO_test_001",
            phone_number="254700000001",
            amount_gross=500,
            platform_fee=20,
            amount_net=480,
        )

    def _post_callback(self, result_code=0, receipt="ABC123"):
        payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "mr_001",
                    "CheckoutRequestID": "ws_CO_test_001",
                    "ResultCode": result_code,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 500},
                            {"Name": "MpesaReceiptNumber", "Value": receipt},
                            {"Name": "TransactionDate", "Value": 20241101120000},
                            {"Name": "PhoneNumber", "Value": 254700000001},
                        ]
                    },
                }
            }
        }
        return self.client.post(
            "/api/payment/callback/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_successful_callback_marks_session_paid(self):
        resp = self._post_callback(result_code=0, receipt="XYZ9999")
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertTrue(self.session.is_paid)

    def test_successful_callback_credits_wallet(self):
        initial = self.profile.wallet_balance
        self._post_callback(result_code=0)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, initial + 480)

    def test_failed_callback_does_not_mark_paid(self):
        self._post_callback(result_code=1)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_paid)

    def test_unknown_checkout_id_returns_200(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "nonexistent_id",
                    "ResultCode": 0,
                    "ResultDesc": "OK",
                }
            }
        }
        resp = self.client.post(
            "/api/payment/callback/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_bad_payload_returns_400(self):
        resp = self.client.post(
            "/api/payment/callback/",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class PaymentStatusViewTests(TestCase):
    def setUp(self):
        _, self.profile = make_consultant()
        self.session = ChatSession.objects.create(
            tenant=self.profile,
            client_display_name="Dave",
            session_token="tok_status",
        )

    def test_returns_unpaid_by_default(self):
        resp = self.client.get(f"/api/payment/status/{self.session.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_paid"])

    def test_returns_paid_after_payment(self):
        self.session.is_paid = True
        self.session.save()
        resp = self.client.get(f"/api/payment/status/{self.session.id}/")
        self.assertTrue(resp.json()["is_paid"])


class RegistrationTests(TestCase):
    def test_register_creates_tenant_profile(self):
        resp = self.client.post(
            "/register/",
            {
                "username": "newuser",
                "password1": "Secr3tP@ss!",
                "password2": "Secr3tP@ss!",
                "display_name": "New Expert",
                "slug": "new_expert",
                "hourly_rate": "750",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(TenantProfile.objects.filter(slug="new_expert").exists())
