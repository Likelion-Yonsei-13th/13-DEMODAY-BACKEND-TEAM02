from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ChatMessage, ChatRoom

@receiver(post_save, sender=ChatMessage)
def update_room_summary_on_message(sender, instance: ChatMessage, created, **kwargs):
    """
    새 메시지가 생성되면 같은 트랜잭션 내에서(가능한 범위) 방 요약을 갱신.
    """
    if not created:
        return
    room = instance.room
    # 가장 최근 메시지 = 방 요약
    if (room.last_msg_id != instance.id) or (room.last_msg_at != instance.created_at):
        ChatRoom.objects.filter(pk=room.pk).update(
            last_msg_id=instance.id, last_msg_at=instance.created_at
        )
