from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ChatMessage, ChatRoom


@receiver(post_save, sender=ChatMessage)
def update_room_summary_on_message(sender, instance: ChatMessage, created, raw=False, **kwargs):
    """
    새 메시지 생성 시 방 요약(last_msg, last_msg_at)을 최신으로 갱신.
    트랜잭션 커밋 후 반영(on_commit)하여 일관성 보강.
    """
    if raw or not created:
        return

    room_id = instance.room_id
    msg_id = instance.id
    created_at = instance.created_at

    def _update():
        ChatRoom.objects.filter(pk=room_id).update(
            last_msg_id=msg_id,
            last_msg_at=created_at,
        )
    transaction.on_commit(_update)


@receiver(post_save, sender=ChatMessage)
def refresh_room_summary_on_soft_delete(sender, instance: ChatMessage, created, raw=False, **kwargs):
    """
    메시지가 수정되어 is_deleted=True가 되었고,
    그것이 room의 last_msg였다면 최신 '삭제되지 않은' 메시지로 다시 요약을 맞춘다.
    """
    if raw or created or not instance.is_deleted:
        return

    room = instance.room
    if room.last_msg_id != instance.id:
        return

    latest = (
        ChatMessage.objects
        .filter(room_id=room.id, is_deleted=False)
        .order_by("-created_at", "-id")
        .only("id", "created_at")
        .first()
    )

    def _update():
        if latest:
            ChatRoom.objects.filter(pk=room.pk).update(
                last_msg_id=latest.id,
                last_msg_at=latest.created_at,
            )
        else:
            ChatRoom.objects.filter(pk=room.pk).update(
                last_msg_id=None,
                last_msg_at=None,
            )
    transaction.on_commit(_update)
