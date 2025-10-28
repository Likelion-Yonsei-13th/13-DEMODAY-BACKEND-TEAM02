import uuid
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth import logout as django_logout
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer,
    InterestSerializer,
    InstagramRequestSerializer,
    InstagramStatusSerializer,
    InstagramConfirmSerializer,
    LocalProfileSerializer,
    UserProfileSerializer,
)
from .models import Interest, InstagramVerification, LocalProfile, UserProfile

User = get_user_model()


# ------------------------
# Auth (회원가입/인증/로그인/로그아웃)
# ------------------------
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = UserRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()

        # 이메일 인증 토큰 발급 & 저장
        token = uuid.uuid4()
        user.email_verification_token = token
        user.save(update_fields=["email_verification_token"])

        verify_path = reverse("verify-email", args=[str(token)])
        verify_link = request.build_absolute_uri(verify_path)

        send_mail(
            subject="[Demo] 이메일 인증을 완료해주세요",
            message=f"아래 링크를 눌러 인증을 완료하세요:\n{verify_link}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=True,
        )

        return Response(
            {"message": "회원가입 완료. 이메일을 확인해주세요."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        # token(str) -> UUID 검증
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

        return Response(
            {
                "message": "이메일 인증 완료",
                "role": user.role,
                "next_step": compute_next_step(user),
            },
            status=200,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = UserLoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data["user"]

        # JWT 발급
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh = str(refresh)

        res = Response(
            {
                "message": "로그인 성공",
                "role": user.role,
                "next_step": compute_next_step(user),
            },
            status=200,
        )

        # HttpOnly 쿠키 저장 (운영에서는 secure=True 권장)
        res.set_cookie(
            "access_token",
            access,
            httponly=True,
            samesite="Lax",
            secure=False,
            path="/",
        )
        res.set_cookie(
            "refresh_token",
            refresh,
            httponly=True,
            samesite="Lax",
            secure=False,
            path="/",
        )
        return res


class LogoutView(APIView):
    def post(self, request):
        django_logout(request)  # 세션 로그아웃(세션 미사용 시 영향 미미)
        res = Response({"message": "로그아웃 완료"}, status=200)
        res.delete_cookie("access_token", path="/")
        res.delete_cookie("refresh_token", path="/")
        return res


# ------------------------
# 역할별 권한
# ------------------------
class IsLocal(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.LOCAL


class IsTraveler(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.USER


# ------------------------
# 온보딩 단계 계산
# ------------------------
# views.py


def compute_next_step(user: User) -> str:
    # 이메일 인증 미완료면 우선
    if not user.is_active:
        return "EMAIL_VERIFY"

    if user.role == User.Role.LOCAL:
        # 로컬 프로필이 없으면 생성만 해두고 관심사 확인
        lp, _ = LocalProfile.objects.get_or_create(user=user)
        if lp.interests.count() == 0:
            return "SELECT_INTERESTS_LOCAL"
        return "DONE"

    else:  # USER
        up, _ = UserProfile.objects.get_or_create(user=user)
        if up.interests.count() == 0:
            return "SELECT_INTERESTS_USER"
        return "DONE"


class OnboardingNextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        step = compute_next_step(request.user)
        return Response(
            {
                "role": request.user.role,
                "next_step": step,
                "hints": {
                    "EMAIL_VERIFY": "이메일 인증을 완료해주세요.",
                    "SELECT_INTERESTS_USER": "여행자 관심사(카테고리)를 선택하세요.",
                    "SELECT_INTERESTS_LOCAL": "로컬 관심사(카테고리)를 선택하세요.",
                    "DONE": "완료되었습니다.",
                },
            }
        )


# ------------------------
# Interests
# ------------------------
class InterestListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = InterestSerializer

    def get_queryset(self):
        return Interest.objects.order_by("name")


# ------------------------
# Instagram Verification (Local 전용)
# ------------------------
class InstagramRequestView(generics.CreateAPIView):
    permission_classes = [IsLocal]
    serializer_class = InstagramRequestSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        iv = ser.save()
        return Response(InstagramStatusSerializer(iv).data, status=201)


class InstagramStatusView(generics.RetrieveAPIView):
    permission_classes = [IsLocal]
    serializer_class = InstagramStatusSerializer

    def get_object(self):
        return InstagramVerification.objects.get(user=self.request.user)


class InstagramConfirmView(generics.CreateAPIView):
    permission_classes = [IsLocal]
    serializer_class = InstagramConfirmSerializer

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        iv = ser.save()
        return Response(InstagramStatusSerializer(iv).data, status=200)


# ------------------------
# Profiles
# ------------------------
class LocalProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsLocal]
    serializer_class = LocalProfileSerializer

    def get_object(self):
        obj, _ = LocalProfile.objects.get_or_create(user=self.request.user)
        return obj


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsTraveler]
    serializer_class = UserProfileSerializer

    def get_object(self):
        obj, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return obj


# views.py
class SwitchRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        role = request.data.get("role")
        if role not in (User.Role.USER, User.Role.LOCAL):
            return Response({"detail": "role must be 'USER' or 'LOCAL'."}, status=400)

        if request.user.role == role:
            # 같은 역할로 요청해도 다음 단계 계산은 해서 돌려줌
            next_step = compute_next_step(request.user)
            return Response({"role": role, "next_step": next_step}, status=200)

        request.user.role = role
        request.user.save(update_fields=["role"])

        # 전환 직후에도 바로 다음 단계 알려주기
        next_step = compute_next_step(request.user)
        return Response({"role": role, "next_step": next_step}, status=200)
