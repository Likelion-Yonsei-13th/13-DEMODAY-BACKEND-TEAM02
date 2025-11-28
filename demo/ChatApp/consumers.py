from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        self.group_name = f"chat_{self.room_id}"
        user = self.scope.get("user")

        # 1) 인증 확인
        if not user or isinstance(user, AnonymousUser):
            await self.close(code=4001)  # 인증 실패
            return

        # 2) 방 참여자인지 확인
        is_participant = await self._is_participant(user, self.room_id)
        if not is_participant:
            await self.close(code=4003)  # 권한 없음
            return

        # 3) 그룹 join + 연결 허용
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _is_participant(self, user, room_id):
        try:
            room = ChatRoom.objects.get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return False
        return user in (room.requester, room.proposer)

    async def receive_json(self, content, **kwargs):
        """
        클라이언트가 보내는 JSON 포맷 예시:
        {
          "msg_type": "TEXT",   // or "IMAGE"
          "body": "안녕!",
          "image_url": null,
          "image_size_bytes": null
        }
        """
        user = self.scope["user"]
        msg_type = content.get("msg_type", ChatMessage.Type.TEXT)
        body = content.get("body")
        image_url = content.get("image_url")
        image_size_bytes = content.get("image_size_bytes")

        # DB에 메시지 저장
        message = await self._create_message(
            user, msg_type, body, image_url, image_size_bytes
        )

        # 같은 방 그룹에 브로드캐스트
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",  # handler 이름
                "message": {
                    "id": message.id,
                    "room": message.room_id,
                    "sender": message.sender_id,
                    "msg_type": message.msg_type,
                    "body": message.body,
                    "image_url": message.image_url,
                    "image_size_bytes": message.image_size_bytes,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    @database_sync_to_async
    def _create_message(self, user, msg_type, body, image_url, image_size_bytes):
        # ChatMessage.clean() 에서 TEXT/IMAGE 조건 검증해줄 것
        room = ChatRoom.objects.get(pk=self.room_id)

        message = ChatMessage.objects.create(
            room=room,
            sender=user,
            msg_type=msg_type,
            body=body,
            image_url=image_url,
            image_size_bytes=image_size_bytes,
        )

        # ChatRoom 마지막 메시지 갱신
        room.last_msg = message
        room.last_msg_at = message.created_at
        room.save(update_fields=["last_msg", "last_msg_at"])

        return message

    async def chat_message(self, event):
        """
        group_send 의 "type": "chat.message" 가 오면 호출되는 핸들러
        """
        await self.send_json(event["message"])

    async def chat_room_status(self, event):
        await self.send_json(event["message"])
