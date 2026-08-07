import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class TenantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="tenant_profile")
    slug = models.SlugField(unique=True, max_length=60, help_text="URL username, e.g. legal_expert")
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subscription_status = models.BooleanField(default=False)
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def subscription_is_active(self):
        return self.subscription_status and (
            self.subscription_expires_at is None
            or self.subscription_expires_at > timezone.now()
        )

    def __str__(self):
        return f"{self.slug} ({self.user.email})"


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name="chat_sessions")
    client_display_name = models.CharField(max_length=80)
    session_token = models.CharField(max_length=64, unique=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_display_name} → {self.tenant.slug}"


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        AUDIO = "audio", "Audio"
        IMAGE = "image", "Image"

    class MessageStatus(models.TextChoices):
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender_id = models.CharField(max_length=80)  # slug for consultant, display_name for client
    is_from_consultant = models.BooleanField(default=False)
    type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    status = models.CharField(
        max_length=10, choices=MessageStatus.choices, default=MessageStatus.SENT
    )
    reactions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.type}] {self.sender_id}: {self.content[:40]}"


class MpesaTransaction(models.Model):
    class TransactionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name="mpesa_transactions")
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="mpesa_transactions")
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    mpesa_receipt_number = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=20)
    amount_gross = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=20)
    amount_net = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=TransactionStatus.choices, default=TransactionStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mpesa_receipt_number or self.checkout_request_id} – {self.status}"
