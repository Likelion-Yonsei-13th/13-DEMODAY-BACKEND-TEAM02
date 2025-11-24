import os
from django.core.asgi import get_asgi_application

# 1) 가장 먼저 settings 모듈 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

# 2) Django 앱 로딩 (INSTALLED_APPS 초기화)
django_asgi_app = get_asgi_application()

# 3) 그 다음에야 Channels/미들웨어/라우팅 import
from channels.routing import ProtocolTypeRouter, URLRouter
from account.jwt_ws_middleware import JwtAuthMiddlewareStack
import ChatApp.routing  # INSTALLED_APPS 에 "ChatApp" 이 있으니 이 이름 사용

# 4) 프로토콜별 라우팅 정의
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddlewareStack(
            URLRouter(
                ChatApp.routing.websocket_urlpatterns
            )
        ),
    }
)
