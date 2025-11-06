from django.contrib import admin
from .models import ChatRoom, ChatMessage

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "proposal", "requester", "proposer", "last_msg", "last_msg_at", "created_at")
    list_filter = ("created_at",)
    search_fields = ("proposal__id", "requester__username", "proposer__username")

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "msg_type", "created_at", "is_deleted")
    list_filter = ("msg_type", "is_deleted", "created_at")
    search_fields = ("room__id", "sender__username", "body")
