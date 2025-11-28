from django.urls import path

from .views import (
    ChatRoomListCreateView,
    ChatRoomDetailView,
    ChatMessageListCreateView,
    ChatMessageDetailView,
    ChatImageUploadView,
    ChatRoomFinishView,
)

app_name = "chat"

urlpatterns = [
    path("rooms/", ChatRoomListCreateView.as_view(), name="room-list"),
    path("rooms/<int:pk>/", ChatRoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:room_id>/messages/", ChatMessageListCreateView.as_view(), name="message-list"),
    path("messages/<int:pk>/", ChatMessageDetailView.as_view(), name="message-detail"),
    path("rooms/<int:room_id>/upload-image/", ChatImageUploadView.as_view()),
    path("rooms/<int:room_id>/confirmed/", ChatRoomFinishView.as_view()),
]
