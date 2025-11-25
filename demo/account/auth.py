from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    1순위: Authorization 헤더 (Bearer 토큰)
    2순위: HttpOnly 쿠키 access_token
    둘 중 하나라도 있으면 인증 성공
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None  # 토큰 아예 없으면 "그냥 비로그인" 취급

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            # 🔥 핵심:
            # 토큰이 깨졌거나 만료되었으면
            # "그냥 인증 실패(None)"로 처리해서
            # 퍼블릭 엔드포인트가 401 안 나도록 함
            return None

        return self.get_user(validated_token), validated_token
