from django.conf import settings


def build_daraja_checkout_payload(session_reference, amount, phone_number):
    return {
        "BusinessShortCode": settings.DARAJA_SHORTCODE,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.DARAJA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.DARAJA_CALLBACK_URL,
        "AccountReference": session_reference,
        "TransactionDesc": "Dash consultant session",
        "Environment": settings.DARAJA_ENVIRONMENT,
        "Gateway": settings.PAYMENT_GATEWAY_NAME,
    }
