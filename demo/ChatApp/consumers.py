from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        user = self.scope["user"]
        if isinstance(user, AnonymousUser):
            await self.close()
            return
        allowed = await self._is_participant(user.id, self.room_id)
        if not allowed:
            await self.close()
            return
        self.group = f"room_{self.room_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, *args, **kwargs):
        user = self.scope["user"]
        saved = await self._save_message(user.id, self.room_id, content)
        await self.channel_layer.group_send(self.group, {"type": "broadcast", "message": saved})

    async def broadcast(self, event):
        await self.send_json(event["message"])

    @database_sync_to_async
    def _is_participant(self, user_id, room_id):
        return ChatRoom.objects.filter(
            id=room_id
        ).filter(Q(requester_id=user_id) | Q(proposer_id=user_id)).exists()

    @database_sync_to_async
    def _save_message(self, user_id, room_id, payload):
        msg = ChatMessage.objects.create(
            room_id=room_id,
            sender_id=user_id,
            msg_type=payload.get("msg_type", "TEXT"),
            body=payload.get("body"),
            image_url=payload.get("image_url"),
            image_size_bytes=payload.get("image_size_bytes"),
        )
        return {
            "id": msg.id,
            "room": msg.room_id,
            "sender": msg.sender_id,
            "msg_type": msg.msg_type,
            "body": msg.body,
            "image_url": msg.image_url,
            "created_at": msg.created_at.isoformat(),
        }
