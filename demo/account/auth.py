# account/auth.py

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    1. Authorization 헤더에 Bearer 토큰이 있으면 그걸 우선 사용
    2. 없으면 쿠키(access_token)에서 가져옴
    3. 토큰이 없거나/깨졌거나/만료되면 -> 예외 안 던지고 None 리턴
       => request.user 는 AnonymousUser (비로그인 상태)
    """

    def authenticate(self, request):
        # 1) Authorization 헤더 체크
        header = self.get_header(request)
        raw_token = None

        if header is not None:
            raw_token = self.get_raw_token(header)

        # 2) 헤더에 없으면 쿠키에서 토큰 가져오기
        if raw_token is None:
            raw_token = request.COOKIES.get("access_token")

        # 3) 아예 토큰이 없으면 -> 그냥 비로그인 취급
        if raw_token is None:
            return None

        # 4) 토큰이 있는데 깨졌거나 만료된 경우
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except Exception:
            # ⚠️ 여기서 AuthenticationFailed 를 던지지 않고
            # 그냥 "인증 안 된 상태"로 넘겨버림
            return None
