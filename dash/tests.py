from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from dash.core.services import build_daraja_checkout_payload


@override_settings(
    DARAJA_ENVIRONMENT="sandbox",
    DARAJA_SHORTCODE="174379",
    DARAJA_CALLBACK_URL="https://dash.example.com/payments/mpesa/callback/",
    PAYMENT_GATEWAY_NAME="Stripe",
    DARAJA_DEMO_SESSION_REFERENCE="DASH-DEMO-100",
    DARAJA_DEMO_AMOUNT=2250,
    DARAJA_DEMO_PHONE_NUMBER="254700123456",
)
class DashLandingPageTests(SimpleTestCase):
    def test_homepage_promotes_dash_chat_and_mpesa_daraja(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WhatsApp-style consulting")
        self.assertContains(response, "M-Pesa Daraja")
        self.assertContains(response, "Consultant inbox")
        self.assertContains(response, "Request M-Pesa deposit")
        self.assertContains(response, "174379")
        self.assertContains(response, "https://dash.example.com/payments/mpesa/callback/")
        self.assertContains(response, "DASH-DEMO-100")
        self.assertContains(response, "KES 2250")


class DarajaPayloadTests(SimpleTestCase):
    @override_settings(
        DARAJA_ENVIRONMENT="sandbox",
        DARAJA_SHORTCODE="654321",
        DARAJA_CALLBACK_URL="https://dash.example.com/payments/mpesa/callback/",
        PAYMENT_GATEWAY_NAME="Flutterwave",
    )
    def test_build_daraja_checkout_payload_uses_dash_settings(self):
        payload = build_daraja_checkout_payload(
            session_reference="DASH-HR-77",
            amount=3000,
            phone_number="254711000111",
        )

        self.assertEqual(payload["BusinessShortCode"], "654321")
        self.assertEqual(payload["TransactionType"], "CustomerPayBillOnline")
        self.assertEqual(payload["Amount"], 3000)
        self.assertEqual(payload["PartyA"], "254711000111")
        self.assertEqual(payload["PartyB"], "654321")
        self.assertEqual(payload["PhoneNumber"], "254711000111")
        self.assertEqual(payload["AccountReference"], "DASH-HR-77")
        self.assertEqual(payload["TransactionDesc"], "Dash consultant session")
        self.assertEqual(payload["Environment"], "sandbox")
        self.assertEqual(payload["CallBackURL"], "https://dash.example.com/payments/mpesa/callback/")
        self.assertEqual(payload["Gateway"], "Flutterwave")
