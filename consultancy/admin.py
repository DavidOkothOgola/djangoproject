from django.contrib import admin
from .models import TenantProfile, ChatSession, Message, MpesaTransaction


@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    list_display = ("slug", "display_name", "wallet_balance", "subscription_status", "subscription_expires_at")
    search_fields = ("slug", "display_name", "user__email")
    list_filter = ("subscription_status",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "client_display_name", "is_paid", "created_at")
    list_filter = ("is_paid", "tenant")
    search_fields = ("client_display_name",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_session", "sender_id", "type", "status", "created_at")
    list_filter = ("type", "status")


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ("checkout_request_id", "tenant", "phone_number", "amount_gross", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("checkout_request_id", "mpesa_receipt_number", "phone_number")
