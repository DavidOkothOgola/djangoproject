from django.urls import path

from consultancy.consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<uuid:session_id>/", ChatConsumer.as_asgi()),
]
