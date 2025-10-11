from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, logout
from .serializers import UserRegisterSerializer, UserLoginSerializer
import uuid
from uuid import UUID

User = get_user_model()

class RegisterView(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # ✅ 토큰을 DB에 저장
            token = str(uuid.uuid4())
            user.email_verification_token = token
            user.save()

            send_mail(
                subject='이메일 인증',
                message=f'다음 링크를 클릭하여 이메일을 인증해주세요:\nhttp://localhost:8000/account/verify-email/{token}/',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response({"message": "회원가입 완료. 이메일 인증을 진행해주세요."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    def get(self, request, token):
        try:
            token_uuid = UUID(token)  # 문자열을 UUID로 변환
        except ValueError:
            return Response({"message": "유효하지 않은 토큰입니다."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email_verification_token=token_uuid).first()
        if not user:
            return Response({"message": "유효하지 않은 토큰입니다."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.email_verification_token = None  # 인증 후 제거
        user.save()
        return Response({"message": "이메일 인증이 완료되었습니다."}, status=status.HTTP_200_OK)

class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # ✅ JWT 토큰 발급
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            response = Response({"message": "로그인 성공"}, status=status.HTTP_200_OK)
            response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', secure=False)
            response.set_cookie('refresh_token', refresh_token, httponly=True, samesite='Lax', secure=False)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        response = Response({"message": "로그아웃 완료"}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response