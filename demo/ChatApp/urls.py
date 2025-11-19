from rest_framework_nested import routers
from .views import ChatRoomViewSet, ChatMessageViewSet

router = routers.SimpleRouter()
router.register(r"rooms", ChatRoomViewSet, basename="room")

nested = routers.NestedSimpleRouter(router, r"rooms", lookup="room")
nested.register(r"messages", ChatMessageViewSet, basename="room-messages")

urlpatterns = router.urls + nested.urls
