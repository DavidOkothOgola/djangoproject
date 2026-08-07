import logging
import json
import secrets

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dash.core.services import get_daraja_access_token, daraja_stk_push
from .models import ChatSession, Message, MpesaTransaction, TenantProfile

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Auth views
# ─────────────────────────────────────────────

def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        display_name = request.POST.get("display_name", "").strip()
        slug_input = request.POST.get("slug", "").strip()
        hourly_rate = request.POST.get("hourly_rate", "0")
        if form.is_valid():
            user = form.save()
            slug = slugify(slug_input or user.username)
            base = slug
            counter = 1
            while TenantProfile.objects.filter(slug=slug).exists():
                slug = f"{base}{counter}"
                counter += 1
            TenantProfile.objects.create(
                user=user,
                slug=slug,
                display_name=display_name or user.username,
                hourly_rate=hourly_rate or 0,
            )
            login(request, user)
            return redirect("consultancy:dashboard")
    else:
        form = UserCreationForm()
    return render(request, "consultancy/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("consultancy:dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "consultancy/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("consultancy:login")


@login_required
def dashboard_view(request):
    profile = get_object_or_404(TenantProfile, user=request.user)
    sessions = ChatSession.objects.filter(tenant=profile).order_by("-created_at")[:50]
    return render(request, "consultancy/dashboard.html", {"profile": profile, "sessions": sessions})


# ─────────────────────────────────────────────
# Chat room
# ─────────────────────────────────────────────

def chat_room(request, username):
    tenant = get_object_or_404(TenantProfile, slug=username)
    if not tenant.subscription_is_active():
        return render(request, "consultancy/inactive.html", {"tenant": tenant})

    existing_token = request.session.get(f"dash_token_{username}")
    if existing_token:
        try:
            session = ChatSession.objects.get(session_token=existing_token, tenant=tenant)
            return render(request, "consultancy/chat.html", _chat_context(request, tenant, session))
        except ChatSession.DoesNotExist:
            pass

    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()[:80]
        if not display_name:
            return render(
                request,
                "consultancy/enter_name.html",
                {"tenant": tenant, "error": "Please enter a display name."},
            )
        token = secrets.token_urlsafe(32)
        session = ChatSession.objects.create(
            tenant=tenant, client_display_name=display_name, session_token=token
        )
        request.session[f"dash_token_{username}"] = token
        return render(request, "consultancy/chat.html", _chat_context(request, tenant, session))

    return render(request, "consultancy/enter_name.html", {"tenant": tenant})


def _chat_context(request, tenant, session):
    msgs = session.messages.order_by("created_at")[:100]
    return {
        "tenant": tenant,
        "session": session,
        "messages": msgs,
        "ws_url": f"{'wss' if request.is_secure() else 'ws'}://{request.get_host()}/ws/chat/{session.id}/",
        "sender_id": session.client_display_name,
        "is_consultant": False,
    }


@login_required
def consultant_chat(request, session_id):
    profile = get_object_or_404(TenantProfile, user=request.user)
    session = get_object_or_404(ChatSession, id=session_id, tenant=profile)
    msgs = session.messages.order_by("created_at")[:100]
    context = {
        "tenant": profile,
        "session": session,
        "messages": msgs,
        "ws_url": f"{'wss' if request.is_secure() else 'ws'}://{request.get_host()}/ws/chat/{session.id}/",
        "sender_id": profile.slug,
        "is_consultant": True,
    }
    return render(request, "consultancy/chat.html", context)


# ─────────────────────────────────────────────
# M-Pesa / Daraja
# ─────────────────────────────────────────────

@require_POST
def stk_push_initiate(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    phone_number = request.POST.get("phone_number", "").strip()
    if not phone_number:
        return JsonResponse({"success": False, "error": "Phone number required."}, status=400)

    amount = session.tenant.hourly_rate or 100
    platform_fee = settings.PLATFORM_TRANSACTION_FEE

    try:
        token = get_daraja_access_token()
        result = daraja_stk_push(
            access_token=token,
            phone_number=phone_number,
            amount=amount,
            account_ref=str(session.id)[:12].upper(),
            description="Dash Consultation",
        )
    except Exception as exc:
        logger.exception("STK push failed: %s", exc)
        return JsonResponse({"success": False, "error": "Payment service unavailable."}, status=503)

    if result.get("ResponseCode") != "0":
        return JsonResponse(
            {"success": False, "error": result.get("ResponseDescription", "STK push failed.")},
            status=400,
        )

    net = float(amount) - platform_fee
    MpesaTransaction.objects.create(
        tenant=session.tenant,
        chat_session=session,
        merchant_request_id=result.get("MerchantRequestID", ""),
        checkout_request_id=result["CheckoutRequestID"],
        phone_number=phone_number,
        amount_gross=amount,
        platform_fee=platform_fee,
        amount_net=max(net, 0),
        status=MpesaTransaction.TransactionStatus.PENDING,
    )

    return JsonResponse(
        {
            "success": True,
            "checkout_request_id": result["CheckoutRequestID"],
            "message": "STK push sent. Please check your phone.",
        }
    )


@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Bad payload"}, status=400)

    try:
        stk_callback = body["Body"]["stkCallback"]
        result_code = stk_callback["ResultCode"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
    except (KeyError, TypeError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Malformed payload"}, status=400)

    try:
        with transaction.atomic():
            txn = MpesaTransaction.objects.select_for_update().get(
                checkout_request_id=checkout_request_id
            )
            if result_code == 0:
                items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                meta = {item["Name"]: item.get("Value") for item in items}
                txn.mpesa_receipt_number = str(meta.get("MpesaReceiptNumber", ""))
                txn.status = MpesaTransaction.TransactionStatus.SUCCESS
                tenant = txn.tenant
                tenant.wallet_balance += txn.amount_net
                tenant.save(update_fields=["wallet_balance"])
                session = txn.chat_session
                session.is_paid = True
                session.save(update_fields=["is_paid"])
            else:
                txn.status = MpesaTransaction.TransactionStatus.FAILED
            txn.save(update_fields=["status", "mpesa_receipt_number"])
    except MpesaTransaction.DoesNotExist:
        logger.warning("Unknown CheckoutRequestID in callback: %s", checkout_request_id)

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# ─────────────────────────────────────────────
# Media upload
# ─────────────────────────────────────────────

@require_POST
def media_upload(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"success": False, "error": "No file provided."}, status=400)

    ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else "bin"
    allowed = {"mp3", "ogg", "webm", "wav", "opus", "jpg", "jpeg", "png", "gif", "webp"}
    if ext not in allowed:
        return JsonResponse({"success": False, "error": "File type not allowed."}, status=400)

    path = default_storage.save(
        f"chat/{session.tenant.slug}/{session.id}/{uploaded.name}", uploaded
    )
    url = default_storage.url(path)
    return JsonResponse({"success": True, "url": url})


def payment_status(request, session_id):
    """Lightweight polling endpoint: returns current is_paid state."""
    session = get_object_or_404(ChatSession, id=session_id)
    return JsonResponse({"is_paid": session.is_paid})
