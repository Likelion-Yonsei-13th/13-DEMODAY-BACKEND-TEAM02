from rest_framework import serializers
from .models import ChatRoom, ChatMessage
from DocumentApp.models import RequestRootMap  # 실제 경로에 맞게 조정


class ChatRoomSerializer(serializers.ModelSerializer):
    requester = serializers.PrimaryKeyRelatedField(read_only=True)
    proposer = serializers.PrimaryKeyRelatedField(read_only=True)
    last_msg = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "proposal",
            "requester",
            "proposer",
            "last_msg",
            "last_msg_at",
            "created_at",
        ]
        read_only_fields = ["requester", "proposer", "last_msg", "last_msg_at", "created_at"]

    def validate_proposal(self, proposal):
        # 제안 1개당 채팅방 1개
        if ChatRoom.objects.filter(proposal=proposal).exists():
            raise serializers.ValidationError("이미 해당 제안에 대한 채팅방이 존재합니다.")
        return proposal

    def create(self, validated_data):
        """
        방 생성 시:
        - proposal(RequestRootMap)에서 requester/proposer 유추
          * requester = proposal.request.user  (여행자)
          * proposer = proposal.root.founder   (로컬)
        - 요청한 유저가 둘 중 한 명인지 검증
        """
        request = self.context["request"]
        user = request.user

        proposal = validated_data["proposal"]          # RequestRootMap 인스턴스
        requester = proposal.request.user              # 여행자
        proposer = proposal.root.founder               # 로컬

        if user not in (requester, proposer):
            raise serializers.ValidationError("이 제안의 참여자가 아니라 채팅방을 만들 수 없습니다.")

        room = ChatRoom.objects.create(
            proposal=proposal,
            requester=requester,
            proposer=proposer,
        )
        return room


from rest_framework import serializers
from .models import ChatRoom, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    # 클라이언트가 직접 안 넣도록 read_only
    room = serializers.PrimaryKeyRelatedField(read_only=True)
    sender = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room",
            "sender",
            "msg_type",
            "body",
            "image_url",
            "image_size_bytes",
            "created_at",
            "is_deleted",
        ]
        read_only_fields = ["room", "sender", "created_at", "is_deleted"]

    def validate(self, attrs):
        msg_type = attrs.get("msg_type", ChatMessage.Type.TEXT)
        body = attrs.get("body")
        image_url = attrs.get("image_url")

        if msg_type == ChatMessage.Type.TEXT and not body:
            raise serializers.ValidationError("TEXT 메시지는 body가 필요합니다.")
        if msg_type == ChatMessage.Type.IMAGE and not image_url:
            raise serializers.ValidationError("IMAGE 메시지는 image_url이 필요합니다.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        # serializer.save(room=room) 로 들어온 room 을 validated_data 에서 뽑아냄
        room = validated_data.pop("room", None)
        if room is None:
            # 이러면 view 쪽에서 room을 안 넘긴 거라 내부 버그
            raise serializers.ValidationError("room 정보가 없습니다.")

        # 방 참여자인지 한 번 더 확인
        if user not in (room.requester, room.proposer):
            raise serializers.ValidationError("이 채팅방의 참여자가 아닙니다.")

        msg = ChatMessage.objects.create(
            room=room,
            sender=user,
            **validated_data,  # 여기엔 이제 room 이 없음
        )

        # 마지막 메시지 정보 업데이트
        room.last_msg = msg
        room.last_msg_at = msg.created_at
        room.save(update_fields=["last_msg", "last_msg_at"])

        return msg

