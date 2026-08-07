import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import ChatSession, Message

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles all real-time events for a Dash consultancy chat room.

    Group name: chat_<session_id>
    Payload envelope: {"type": "<event_type>", ...}

    Supported event types (client → server):
      join_room          – announce presence; returns room history
      send_message       – persist + broadcast a text/audio/image message
      typing_state       – broadcast typing indicator (ephemeral, not persisted)
      message_read       – mark messages as read; broadcast double-blue-tick update

    Supported event types (server → client, via group_send):
      chat_message       – new message broadcast
      typing_broadcast   – typing indicator
      read_receipt       – read-status update
      room_history       – initial message history on join
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group = f"chat_{self.session_id}"

        try:
            self.session = await self._get_session(self.session_id)
        except ChatSession.DoesNotExist:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON payload")
            return

        event_type = data.get("type")

        handlers = {
            "join_room": self._handle_join_room,
            "send_message": self._handle_send_message,
            "typing_state": self._handle_typing_state,
            "message_read": self._handle_message_read,
        }

        handler = handlers.get(event_type)
        if handler is None:
            await self._send_error(f"Unknown event type: {event_type}")
            return

        try:
            await handler(data)
        except Exception as exc:
            logger.exception("Error in ChatConsumer.receive: %s", exc)
            await self._send_error("Internal server error")

    # ------------------------------------------------------------------ #
    # Inbound handlers                                                     #
    # ------------------------------------------------------------------ #

    async def _handle_join_room(self, data):
        """Send recent message history to the newly connected client."""
        messages = await self._get_history(self.session_id)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "room_history",
                    "messages": messages,
                }
            )
        )
        # Mark all messages as delivered now that the client is present
        await self._mark_delivered(self.session_id)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "read_receipt",
                "session_id": str(self.session_id),
                "status": "delivered",
            },
        )

    async def _handle_send_message(self, data):
        """Persist a message then broadcast it to the room group."""
        # Re-fetch from DB to pick up payments made after WebSocket connect
        is_paid = await self._get_is_paid(self.session_id)
        if not is_paid:
            await self._send_error("Session not paid. Please complete M-Pesa payment first.")
            return

        sender_id = data.get("sender_id", "anonymous")
        msg_type = data.get("msg_type", "text")
        content = data.get("content", "")
        media_url = data.get("media_url", "")
        reply_to_id = data.get("reply_to_id")
        is_from_consultant = data.get("is_from_consultant", False)

        msg = await self._save_message(
            session_id=self.session_id,
            sender_id=sender_id,
            is_from_consultant=is_from_consultant,
            msg_type=msg_type,
            content=content,
            media_url=media_url,
            reply_to_id=reply_to_id,
        )

        payload = {
            "type": "chat_message",
            "id": str(msg["id"]),
            "sender_id": msg["sender_id"],
            "is_from_consultant": msg["is_from_consultant"],
            "msg_type": msg["type"],
            "content": msg["content"],
            "media_url": msg["media_url"],
            "reply_to_id": str(reply_to_id) if reply_to_id else None,
            "status": msg["status"],
            "created_at": msg["created_at"],
        }

        await self.channel_layer.group_send(self.room_group, payload)

    async def _handle_typing_state(self, data):
        """Broadcast ephemeral typing state — never persisted."""
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "typing_broadcast",
                "sender_id": data.get("sender_id", "anonymous"),
                "is_typing": data.get("is_typing", False),
            },
        )

    async def _handle_message_read(self, data):
        """Mark messages as read and broadcast double-blue-tick update."""
        reader_id = data.get("reader_id", "anonymous")
        await self._mark_read(self.session_id, reader_id)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "read_receipt",
                "session_id": str(self.session_id),
                "reader_id": reader_id,
                "status": "read",
            },
        )

    # ------------------------------------------------------------------ #
    # Group → channel message handlers (called by channels dispatch)      #
    # ------------------------------------------------------------------ #

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing_broadcast(self, event):
        await self.send(text_data=json.dumps(event))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps(event))

    async def room_history(self, event):
        await self.send(text_data=json.dumps(event))

    # ------------------------------------------------------------------ #
    # Database helpers                                                     #
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def _get_session(self, session_id):
        return ChatSession.objects.select_related("tenant").get(id=session_id)

    @database_sync_to_async
    def _get_history(self, session_id):
        msgs = Message.objects.filter(chat_session_id=session_id).select_related("reply_to")[:100]
        result = []
        for m in msgs:
            result.append(
                {
                    "id": str(m.id),
                    "sender_id": m.sender_id,
                    "is_from_consultant": m.is_from_consultant,
                    "type": m.type,
                    "content": m.content,
                    "media_url": m.media_url,
                    "reply_to_id": str(m.reply_to_id) if m.reply_to_id else None,
                    "status": m.status,
                    "reactions": m.reactions,
                    "created_at": m.created_at.strftime("%H:%M"),
                }
            )
        return result

    @database_sync_to_async
    def _save_message(
        self, session_id, sender_id, is_from_consultant, msg_type, content, media_url, reply_to_id
    ):
        msg = Message.objects.create(
            chat_session_id=session_id,
            sender_id=sender_id,
            is_from_consultant=is_from_consultant,
            type=msg_type,
            content=content,
            media_url=media_url,
            reply_to_id=reply_to_id if reply_to_id else None,
            status=Message.MessageStatus.SENT,
        )
        return {
            "id": str(msg.id),
            "sender_id": msg.sender_id,
            "is_from_consultant": msg.is_from_consultant,
            "type": msg.type,
            "content": msg.content,
            "media_url": msg.media_url,
            "status": msg.status,
            "created_at": msg.created_at.strftime("%H:%M"),
        }

    @database_sync_to_async
    def _get_is_paid(self, session_id):
        return ChatSession.objects.values_list("is_paid", flat=True).get(id=session_id)

    @database_sync_to_async
    def _mark_delivered(self, session_id):
        Message.objects.filter(
            chat_session_id=session_id, status=Message.MessageStatus.SENT
        ).update(status=Message.MessageStatus.DELIVERED)

    @database_sync_to_async
    def _mark_read(self, session_id, reader_id):
        Message.objects.filter(
            chat_session_id=session_id, status=Message.MessageStatus.DELIVERED
        ).exclude(sender_id=reader_id).update(status=Message.MessageStatus.READ)

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({"type": "error", "message": message}))
