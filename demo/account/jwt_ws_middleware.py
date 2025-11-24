from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication


def _get_raw_token_from_scope(scope):
    """
    1순위: Authorization 헤더의 Bearer 토큰
    2순위: Cookie 헤더의 access_token
    3순위(선택): 쿼리스트링 ?token=... (원하면 사용)
    """
    headers = dict(scope.get("headers", []))  # {b'header-name': b'value'}

    # 1) Authorization: Bearer xxx
    auth = headers.get(b"authorization")
    if auth:
        try:
            text = auth.decode()
            if text.lower().startswith("bearer "):
                return text.split()[1]
        except Exception:
            pass

    # 2) Cookie: access_token=...
    cookie = headers.get(b"cookie")
    if cookie:
        try:
            cookie_str = cookie.decode()
            for part in cookie_str.split(";"):
                if "=" in part:
                    name, value = part.strip().split("=", 1)
                    if name == "access_token":
                        return value
        except Exception:
            pass

    # 3) querystring token (선택)
    query_string = scope.get("query_string", b"")
    if query_string:
        try:
            qs = parse_qs(query_string.decode())
            if "token" in qs:
                return qs["token"][0]
        except Exception:
            pass

    return None


class JwtWebsocketAuthMiddleware:
    """
    WebSocket handshake 시 JWT(access_token) 을 읽어서 scope["user"] 에 넣어주는 미들웨어
    """

    def __init__(self, inner):
        self.inner = inner
        self.jwt_auth = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        close_old_connections()

        raw_token = _get_raw_token_from_scope(scope)
        user = AnonymousUser()

        if raw_token:
            try:
                validated = self.jwt_auth.get_validated_token(raw_token)
                # get_user 는 DB를 치므로 async wrapper 필요
                user = await database_sync_to_async(self.jwt_auth.get_user)(validated)
            except Exception:
                # 토큰이 이상하면 AnonymousUser 로 둠
                user = AnonymousUser()

        scope["user"] = user
        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """
    사용 편의를 위한 helper. (나중에 Session 기반 AuthMiddlewareStack 과 섞고 싶으면 여기서 감싸도 됨)
    """
    return JwtWebsocketAuthMiddleware(inner)
