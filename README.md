# Dash

Dash is a Django project for consultant conversations with a WhatsApp-style chat experience and M-Pesa Daraja payment wiring.

## Features

- Dash-branded Django project package
- WhatsApp-inspired consultant inbox and active chat thread
- M-Pesa Daraja checkout payload wiring for consultation billing
- Secondary payment gateway configuration for non-M-Pesa clients

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure environment

Copy `.env.example` to `.env` and set your payment values:

- `SECRET_KEY`
- `DARAJA_ENVIRONMENT`
- `DARAJA_SHORTCODE`
- `DARAJA_PASSKEY`
- `DARAJA_CALLBACK_URL`
- `PAYMENT_GATEWAY_NAME`
- `DARAJA_DEMO_SESSION_REFERENCE`
- `DARAJA_DEMO_AMOUNT`
- `DARAJA_DEMO_PHONE_NUMBER`

## Run the application

```bash
python manage.py runserver
```

## Collect static files

```bash
python manage.py collectstatic
```

## Run targeted tests

```bash
python manage.py test dash.tests
```
