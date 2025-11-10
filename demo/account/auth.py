from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    """
    1순위: Authorization 헤더 (Bearer 토큰)
    2순위: HttpOnly 쿠키 access_token
    둘 중 하나라도 있으면 인증 성공
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:                 # 헤더에 있으면 기본 로직 사용
            raw_token = self.get_raw_token(header)
        else:                                  # 없으면 쿠키에서 시도
            raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
