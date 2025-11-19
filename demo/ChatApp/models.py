from django.conf import settings
from django.db import models


# 룸: 제안(RequestRootMap) 1건당 1개의 채팅방 (1:1)
class ChatRoom(models.Model):
    proposal = models.OneToOneField(
        "DocumentApp.RequestRootMap",
        on_delete=models.CASCADE,
        related_name="chat_room",
    )
    # 조회 최적화를 위한 참여자 중복 저장(denormalize)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chat_rooms_as_requester",
    )
    proposer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chat_rooms_as_proposer",
    )

    # 마지막 메시지 요약(정렬/목록용)
    last_msg = models.ForeignKey(
        "ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",  # 역참조 불필요
    )
    last_msg_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_room"
        indexes = [
            models.Index(fields=["last_msg_at"]),                # 최신순 정렬
            models.Index(fields=["requester", "last_msg_at"]),   # 내 방 목록 (요청자)
            models.Index(fields=["proposer", "last_msg_at"]),    # 내 방 목록 (제안자)
        ]

    def __str__(self):
        return f"Room#{self.pk} proposal={self.proposal_id}"


class ChatMessage(models.Model):
    class Type(models.TextChoices):
        TEXT = "TEXT", "TEXT"
        IMAGE = "IMAGE", "IMAGE"

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_messages"
    )

    msg_type = models.CharField(max_length=8, choices=Type.choices, default=Type.TEXT)
    body = models.CharField(max_length=512, null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)

    image_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_message"
        indexes = [
            models.Index(fields=["room", "id"]),                        # 키셋 페이지네이션
            models.Index(fields=["room", "created_at"]),                # 시간순
            models.Index(fields=["room", "is_deleted", "created_at"]),  # ✅ 삭제 제외 조회 최적화
        ]
        ordering = ("-created_at", "-id")

    def clean(self):
        from django.core.exceptions import ValidationError

        # 타입별 필수/금지 필드 검증
        if self.msg_type == self.Type.TEXT:
            if not self.body:
                raise ValidationError("TEXT 메시지는 body가 필요합니다.")
            # TEXT에서는 이미지 관련 필드를 비움
            self.image_url = None
            self.image_size_bytes = None

        elif self.msg_type == self.Type.IMAGE:
            if not self.image_url:
                raise ValidationError("IMAGE 메시지는 image_url이 필요합니다.")

        super().clean()

    def __str__(self):
        return f"Msg#{self.pk} room={self.room_id} type={self.msg_type}"
