# ChatApp/serializers.py
from rest_framework import serializers
from .models import ChatRoom, ChatMessage

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = (
            "id","room","sender","msg_type","body",
            "image_url","image_size_bytes","created_at","is_deleted"
        )
        read_only_fields = ("id","created_at","is_deleted")

    def validate(self, data):
        t = data.get("msg_type")
        body = data.get("body")
        url = data.get("image_url")
        size = data.get("image_size_bytes")

        if t == ChatMessage.Type.TEXT:
            if not body or not str(body).strip():
                raise serializers.ValidationError("TEXT 메시지는 body가 필요합니다.")
            data["image_url"] = None
            data["image_size_bytes"] = None

        elif t == ChatMessage.Type.IMAGE:
            if not url:
                raise serializers.ValidationError("IMAGE 메시지는 image_url이 필요합니다.")
            if size is None or size <= 0 or size > MAX_IMAGE_BYTES:
                raise serializers.ValidationError("image_size_bytes가 유효하지 않거나 10MB 초과입니다.")
            data["body"] = None

        else:
            raise serializers.ValidationError("알 수 없는 메시지 타입입니다.")
        return data


class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ("id","proposal","requester","proposer","last_msg","last_msg_at","created_at")
        read_only_fields = ("id","last_msg","last_msg_at","created_at")
