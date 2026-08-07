from django.conf import settings
from django.shortcuts import render

from dash.core.services import build_daraja_checkout_payload


def index(request):
    active_session = {
        "consultant": "Amina Legal",
        "specialty": "Commercial contracts",
        "rate": "KES 4,500 / hour",
        "status": "Consultation live · 18 mins billed",
        "messages": [
            {
                "author": "client",
                "time": "09:12",
                "text": "Morning Amina, can you review the supplier exit clause before I sign?",
            },
            {
                "author": "consultant",
                "time": "09:13",
                "text": "Yes — upload the clause here and I’ll flag the liability and notice period risks.",
            },
            {
                "author": "client",
                "time": "09:17",
                "text": "Perfect. I’ve prepaid the first 30 minutes through M-Pesa.",
            },
        ],
    }
    daraja_payload = build_daraja_checkout_payload(
        session_reference="DASH-LEGAL-2048",
        amount=2250,
        phone_number="254700123456",
    )
    context = {
        "title": "Dash",
        "headline": "Dash brings WhatsApp-style consulting together with M-Pesa Daraja billing",
        "subheadline": (
            "Run consultant conversations in a familiar chat layout, meter every session, "
            "and trigger Daraja checkout while keeping a backup payment gateway ready."
        ),
        "sidebar_chats": [
            {"name": "Amina Legal", "snippet": "Liability clause looks risky.", "time": "09:17", "active": True},
            {"name": "Dr. Kendi HR", "snippet": "Interview panel starts at 2 PM.", "time": "Yesterday", "active": False},
            {"name": "Brian Tax", "snippet": "VAT treatment confirmed.", "time": "Wed", "active": False},
        ],
        "active_session": active_session,
        "product_features": [
            "WhatsApp-like chat list, thread view, and quick message composer",
            "Consultant rates, billable timers, and consultation payment prompts",
            f"M-Pesa Daraja STK push wired for {settings.DARAJA_ENVIRONMENT} with shortcode {settings.DARAJA_SHORTCODE}",
            f"Fallback gateway ready through {settings.PAYMENT_GATEWAY_NAME}",
        ],
        "payment_summary": {
            "gateway_name": settings.PAYMENT_GATEWAY_NAME,
            "daraja_environment": settings.DARAJA_ENVIRONMENT,
            "shortcode": settings.DARAJA_SHORTCODE,
            "callback_url": settings.DARAJA_CALLBACK_URL,
            "session_reference": daraja_payload["AccountReference"],
            "amount": daraja_payload["Amount"],
            "phone_number": daraja_payload["PhoneNumber"],
            "transaction_type": daraja_payload["TransactionType"],
        },
        "daraja_payload": daraja_payload,
    }
    return render(request, "index.html", context)
