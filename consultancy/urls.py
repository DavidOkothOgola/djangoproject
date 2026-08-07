from django.urls import path

from . import views

app_name = "consultancy"

urlpatterns = [
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Consultant dashboard
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/chat/<uuid:session_id>/", views.consultant_chat, name="consultant_chat"),
    # Client chat room (public, no login)
    path("<str:username>/", views.chat_room, name="chat_room"),
    # Payments
    path("api/payment/stk/<uuid:session_id>/", views.stk_push_initiate, name="stk_push"),
    path("api/payment/callback/", views.mpesa_callback, name="mpesa_callback"),
    # Media
    path("api/upload/<uuid:session_id>/", views.media_upload, name="media_upload"),
    # Payment status polling
    path("api/payment/status/<uuid:session_id>/", views.payment_status, name="payment_status"),
]
