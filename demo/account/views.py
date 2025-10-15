import uuid
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth import logout as django_logout
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserRegisterSerializer, UserLoginSerializer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = UserRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()

        # 이메일 인증 토큰 발급 & 저장
        token = uuid.uuid4()
        user.email_verification_token = token
        user.save(update_fields=["email_verification_token"])

        # 메일에 포함할 인증 링크 (경로 파라미터 사용)
        verify_path = reverse('verify-email', args=[str(token)])
        verify_link = request.build_absolute_uri(verify_path)

        send_mail(
            subject="이메일 인증을 완료해주세요",
            message=f"아래 링크를 클릭하여 이메일 인증을 완료하세요:\n{verify_link}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"message": "회원가입 완료. 이메일을 확인해주세요."},
                        status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    # URL 경로에서 token 문자열을 받아서 UUID로 검증
    def get(self, request, token):
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return Response({"detail": "토큰 형식이 올바르지 않습니다."}, status=400)

        user = User.objects.filter(email_verification_token=token_uuid).first()
        if not user:
            return Response({"detail": "유효하지 않은 토큰입니다."}, status=400)

        user.is_active = True
        user.email_verification_token = None
        user.save(update_fields=["is_active", "email_verification_token"])
        return Response({"message": "이메일 인증이 완료되었습니다."}, status=200)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = UserLoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data["user"]

        # JWT 발급
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh = str(refresh)

        res = Response({"message": "로그인 성공"}, status=200)

        # HttpOnly 쿠키 저장 (운영에서는 secure=True 권장)
        res.set_cookie(
            "access_token", access,
            httponly=True, samesite="Lax", secure=False, path="/",
        )
        res.set_cookie(
            "refresh_token", refresh,
            httponly=True, samesite="Lax", secure=False, path="/",
        )
        return res


class LogoutView(APIView):
    def post(self, request):
        django_logout(request)  # 세션 로그아웃(세션 미사용 시 영향 미미)
        res = Response({"message": "로그아웃 완료"}, status=200)
        res.delete_cookie("access_token", path="/")
        res.delete_cookie("refresh_token", path="/")
        return res