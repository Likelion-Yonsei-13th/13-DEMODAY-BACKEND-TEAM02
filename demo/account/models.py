from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
import uuid
import random
import string


# ------------------------
# User & Manager
# ------------------------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("아이디(username)는 필수입니다.")
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        # 기본적으로 이메일 인증 전까지 비활성
        user.is_active = extra_fields.get("is_active", False)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)  # 어드민은 활성
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        USER = "USER", "User"

    # 기본 id 제거하고 uuid(BigInt) 를 PK로 사용
    id = None
    uuid = models.BigAutoField(primary_key=True)

    # AbstractUser 에 username 이미 존재 (로그인 ID)
    email = models.EmailField(unique=True)

    # 역할 / 닉네임
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    display_name = models.CharField(max_length=50)

    # 기본 정보
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)

    # 약관 동의 정보 (회원가입 화면 체크박스)
    is_over_14 = models.BooleanField(default=False)
    agreed_service_terms = models.BooleanField(default=False)
    agreed_privacy = models.BooleanField(default=False)
    agreed_marketing = models.BooleanField(default=False)  # 선택 동의

    # 나중에 채팅 / 위시리스트 모델 만들면 FK로 교체 예정
    chatroom_id = models.BigIntegerField(null=True, blank=True)
    wishlist_id = models.BigIntegerField(null=True, blank=True)

    # 가입일시
    created_at = models.DateTimeField(auto_now_add=True)

    # 이메일 인증용 토큰(일회성)
    email_verification_token = models.UUIDField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    def __str__(self):
        return self.username


# ------------------------
# Onboarding Domain
# ------------------------
class Interest(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    def __str__(self):
        return self.name


def _gen_code(length: int = 6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


class InstagramVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instagram_verification",
    )
    handle = models.CharField(max_length=50)
    code = models.CharField(max_length=12, default=_gen_code)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    proof_url = models.URLField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - @{self.handle} ({self.status})"


class BaseProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=50, blank=True)
    photo_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    languages = models.JSONField(default=list, blank=True)  # ["ko","en"]
    interests = models.ManyToManyField(Interest, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user.username}"


class LocalProfile(BaseProfile):
    regions = models.JSONField(default=list, blank=True)  # ["Seoul","Busan"]
    strengths = models.JSONField(default=list, blank=True)  # ["야경사진","K-POP"]
    portfolio = models.JSONField(
        default=list, blank=True
    )  # [{title, image_url, desc, coordinates:[{lat,lng}]}]

    @property
    def instagram_verified(self) -> bool:
        iv = getattr(self.user, "instagram_verification", None)
        return bool(iv and iv.status == InstagramVerification.Status.VERIFIED)


class UserProfile(BaseProfile):
    mbti = models.CharField(max_length=4, blank=True)
    travel_style = models.CharField(max_length=100, blank=True)