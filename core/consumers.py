"""
WebSocket consumer for live chat.
Authenticates via JWT in query string; one room per conversation (canonical key from user ids).
"""
import json
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from django.contrib.auth.models import AnonymousUser
from core.models import User, LiveChatMessage
from core.chat_utils import can_chat_with

# Number of recent messages to send when opening a conversation
CHAT_HISTORY_LIMIT = 50


def get_room_name(user_id_1, user_id_2):
    """Canonical room name for the conversation between two users."""
    lo, hi = min(user_id_1, user_id_2), max(user_id_1, user_id_2)
    return f"chat_{lo}_{hi}"


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = None
        self.user = AnonymousUser()

        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token", [])
        token = token_list[0] if token_list else None

        if not token:
            await self.close(code=4401)
            return

        try:
            access = AccessToken(token)
            user_id = access.get("user_id")
        except (InvalidToken, TokenError, KeyError):
            await self.close(code=4401)
            return

        user = await sync_to_async(User.objects.filter(id=user_id).first)()
        if user is None:
            await self.close(code=4401)
            return

        self.user = user
        self.scope["user"] = user
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_name:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        if self.user.is_anonymous:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        msg_type = data.get("type")

        if msg_type == "open_conversation":
            other_user_id = data.get("other_user_id")
            if other_user_id is None:
                await self.send(text_data=json.dumps({"type": "error", "message": "other_user_id required"}))
                return
            try:
                other_user_id = int(other_user_id)
            except (TypeError, ValueError):
                await self.send(text_data=json.dumps({"type": "error", "message": "Invalid other_user_id"}))
                return

            other_user = await sync_to_async(User.objects.filter(id=other_user_id).first)()
            if other_user is None:
                await self.send(text_data=json.dumps({"type": "error", "message": "User not found"}))
                return

            if not await sync_to_async(can_chat_with)(self.user, other_user):
                await self.send(text_data=json.dumps({"type": "error", "message": "Not allowed to chat with this user"}))
                return

            self.room_name = get_room_name(self.user.id, other_user.id)
            await self.channel_layer.group_add(self.room_name, self.channel_name)

            # Send last N messages for this conversation (build payload in sync to avoid ORM in async)
            def _get_history_payload():
                qs = (
                    LiveChatMessage.objects.filter(
                        sender__in=[self.user, other_user],
                        receiver__in=[self.user, other_user],
                    )
                    .select_related("sender", "receiver")
                    .order_by("-created_at")[:CHAT_HISTORY_LIMIT]
                )
                messages = list(qs)[::-1]
                return [
                    {
                        "id": m.id,
                        "sender_id": m.sender_id,
                        "sender_username": m.sender.username,
                        "sender_role": m.sender.role,
                        "receiver_id": m.receiver_id,
                        "message": m.message,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                ]

            payload = await sync_to_async(_get_history_payload)()
            await self.send(text_data=json.dumps({
                "type": "chat_history",
                "messages": payload,
            }))
            return

        if msg_type == "chat_message":
            receiver_id = data.get("receiver_id")
            message_text = (data.get("message") or "").strip()
            if receiver_id is None:
                await self.send(text_data=json.dumps({"type": "error", "message": "receiver_id required"}))
                return
            try:
                receiver_id = int(receiver_id)
            except (TypeError, ValueError):
                await self.send(text_data=json.dumps({"type": "error", "message": "Invalid receiver_id"}))
                return
            if not message_text:
                await self.send(text_data=json.dumps({"type": "error", "message": "message required"}))
                return

            receiver = await sync_to_async(User.objects.filter(id=receiver_id).first)()
            if receiver is None:
                await self.send(text_data=json.dumps({"type": "error", "message": "Receiver not found"}))
                return

            if not await sync_to_async(can_chat_with)(self.user, receiver):
                await self.send(text_data=json.dumps({"type": "error", "message": "Not allowed to chat with this user"}))
                return

            room = get_room_name(self.user.id, receiver.id)
            if self.room_name != room:
                await self.send(text_data=json.dumps({"type": "error", "message": "Open conversation first"}))
                return

            def _save_message_and_payload():
                msg = LiveChatMessage.objects.create(
                    sender=self.user,
                    receiver=receiver,
                    message=message_text,
                )
                return {
                    "type": "chat_message",
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "sender_username": msg.sender.username,
                    "sender_role": msg.sender.role,
                    "receiver_id": msg.receiver_id,
                    "message": msg.message,
                    "created_at": msg.created_at.isoformat(),
                }

            payload = await sync_to_async(_save_message_and_payload)()
            await self.channel_layer.group_send(room, payload)
            return

        await self.send(text_data=json.dumps({"type": "error", "message": "Unknown message type"}))

    async def chat_message(self, event):
        """Receive broadcast from group_send and send to WebSocket."""
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "id": event.get("id"),
            "sender_id": event.get("sender_id"),
            "sender_username": event.get("sender_username"),
            "sender_role": event.get("sender_role"),
            "receiver_id": event.get("receiver_id"),
            "message": event.get("message"),
            "created_at": event.get("created_at"),
        }))
