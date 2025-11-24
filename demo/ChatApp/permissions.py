from rest_framework import permissions
from .models import ChatRoom, ChatMessage


class IsChatParticipant(permissions.BasePermission):
    """
    ChatRoom/ChatMessage 의 requester 또는 proposer 인지 확인
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if isinstance(obj, ChatRoom):
            room = obj
        elif isinstance(obj, ChatMessage):
            room = obj.room
        else:
            return False

        return user.is_authenticated and user in (room.requester, room.proposer)
