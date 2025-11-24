from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 예: ws://localhost:8000/ws/chat/rooms/1/
    re_path(r"ws/chat/rooms/(?P<room_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
]
