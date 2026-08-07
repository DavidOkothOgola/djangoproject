import base64
from datetime import datetime

import requests
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


def get_daraja_access_token():
    """Fetch a short-lived OAuth token from the Daraja API."""
    env = settings.DARAJA_ENVIRONMENT
    base = (
        "https://sandbox.safaricom.co.ke"
        if env == "sandbox"
        else "https://api.safaricom.co.ke"
    )
    resp = requests.get(
        f"{base}/oauth/v1/generate?grant_type=client_credentials",
        auth=(settings.DARAJA_CONSUMER_KEY, settings.DARAJA_CONSUMER_SECRET),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def daraja_stk_push(access_token, phone_number, amount, account_ref, description):
    """Initiate an M-Pesa STK Push via the Daraja API and return the response dict."""
    env = settings.DARAJA_ENVIRONMENT
    base = (
        "https://sandbox.safaricom.co.ke"
        if env == "sandbox"
        else "https://api.safaricom.co.ke"
    )
    shortcode = settings.DARAJA_SHORTCODE
    passkey = settings.DARAJA_PASSKEY
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.DARAJA_CALLBACK_URL,
        "AccountReference": account_ref,
        "TransactionDesc": description,
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{base}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
