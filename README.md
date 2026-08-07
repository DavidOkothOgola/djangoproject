# Dash

Dash is a Django project for real-time consultant conversations with a WhatsApp-style chat experience and M-Pesa Daraja payment integration.

## Features

- **Real-time chat** — WebSocket-powered consultant inbox and active chat threads via Django Channels and Redis
- **WhatsApp-inspired UI** — consultant inbox and active conversation thread
- **M-Pesa Daraja** — STK Push checkout wiring for consultation billing
- **Secondary payment gateway** — configurable for non-M-Pesa clients (e.g. Stripe)
- **Consultancy app** — standalone `consultancy` Django app for managing consultants and sessions
- **Flexible storage** — local file storage by default; S3/Cloudflare R2 optional
- **Flexible database** — SQLite by default; PostgreSQL optional via `DATABASE_URL`

## Project structure

```
djangoproject/
├── dash/                  # Django project package (settings, urls, wsgi, asgi)
│   └── core/              # Core app (models, views, consumers, payments)
├── consultancy/           # Consultancy app (consultants, sessions)
├── manage.py
├── requirements.txt
└── .env.example
```

## Requirements

- Python 3.10+
- Redis (required for WebSocket channel layer)
- PostgreSQL (optional; SQLite used by default)

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### Required

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |

### M-Pesa Daraja

| Variable | Description |
|---|---|
| `DARAJA_ENVIRONMENT` | `sandbox` or `production` |
| `DARAJA_SHORTCODE` | M-Pesa shortcode |
| `DARAJA_PASSKEY` | Daraja passkey from developer portal |
| `DARAJA_CALLBACK_URL` | Public URL for STK Push callbacks |
| `DARAJA_CONSUMER_KEY` | Daraja consumer key |
| `DARAJA_CONSUMER_SECRET` | Daraja consumer secret |
| `PAYMENT_GATEWAY_NAME` | Secondary gateway name (e.g. `Stripe`) |

### Demo / testing

| Variable | Description |
|---|---|
| `DARAJA_DEMO_SESSION_REFERENCE` | Reference used in demo STK Push |
| `DARAJA_DEMO_AMOUNT` | Amount used in demo STK Push |
| `DARAJA_DEMO_PHONE_NUMBER` | Phone used in demo STK Push |

### Real-time (Django Channels)

| Variable | Description |
|---|---|
| `CHANNEL_LAYER_BACKEND` | Default: `channels_redis.core.RedisChannelLayer` |
| `REDIS_URL` | Redis connection URL (default: `redis://localhost:6379`) |

### Database (optional)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL URL — leave empty to use SQLite |

### Media storage (optional)

| Variable | Description |
|---|---|
| `USE_S3` | `True` to enable S3/R2 media storage |
| `AWS_ACCESS_KEY_ID` | S3 / R2 access key |
| `AWS_SECRET_ACCESS_KEY` | S3 / R2 secret key |
| `AWS_STORAGE_BUCKET_NAME` | Bucket name |
| `AWS_S3_ENDPOINT_URL` | Custom endpoint (for Cloudflare R2) |
| `AWS_S3_CUSTOM_DOMAIN` | Custom domain for served media |

> **Note:** For local development, Dash generates an ephemeral `SECRET_KEY` when one is not set, but you should always define a stable key in `.env`.

## Run the development server

Start Redis first (required for WebSocket support):

```bash
redis-server
```

Then run the ASGI development server (Daphne):

```bash
daphne dash.asgi:application
```

Or use the standard Django development server (HTTP only, no WebSockets):

```bash
python manage.py runserver
```

## Apply migrations

```bash
python manage.py migrate
```

## Collect static files

```bash
python manage.py collectstatic
```

## Run tests

```bash
# All tests
python manage.py test

# Targeted
python manage.py test dash.tests
python manage.py test dash.core.tests
```
