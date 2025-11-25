# account/auth.py

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    1. Authorization 헤더에 Bearer 토큰이 있으면 그걸 우선 사용
    2. 없으면 쿠키(access_token)에서 가져옴
    3. 토큰이 없으면 None 리턴 (인증 생략)
    4. 토큰이 있는데 깨졌으면 AuthenticationFailed 예외 발생
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
            if raw_token:
                print(f"[CookieJWTAuth] 쿠키에서 토큰 발견: {raw_token[:20]}...")  # 디버깅

        # 3) 아예 토큰이 없으면 -> 그냥 비로그인 취급
        if raw_token is None:
            print("[CookieJWTAuth] 토큰 없음 (쿠키/헤더 모두 비어있음)")  # 디버깅
            return None

        # 4) 토큰이 있으면 검증
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            print(f"[CookieJWTAuth] 토큰 검증 성공: user={user}")  # 디버깅
            return (user, validated_token)
        except Exception as e:
            print(f"[CookieJWTAuth] 토큰 검증 실패: {e}")  # 디버깅
            # 토큰이 있는데 깨졌으면 None 반환 (다른 인증 방식 시도하도록)
            return None
