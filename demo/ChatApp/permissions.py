from rest_framework.permissions import BasePermission

class IsRoomParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        u = request.user
        if hasattr(obj, "requester"):  # ChatRoom
            return obj.requester_id == u.id or obj.proposer_id == u.id
        if hasattr(obj, "room"):       # ChatMessage
            r = obj.room
            return r.requester_id == u.id or r.proposer_id == u.id
        return False
