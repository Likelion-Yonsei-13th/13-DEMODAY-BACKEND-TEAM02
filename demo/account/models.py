from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

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
        # 이메일 인증 전까지 로그인 불가
        user.is_active = extra_fields.get("is_active", False)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # 관리자 계정은 바로 활성화
        extra_fields.setdefault("is_active", True)
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    # AbstractUser에 username 이미 존재(Unique)
    # 이메일은 인증/알림용으로 Unique 권장
    email = models.EmailField(unique=True)

    # 이메일 인증용 토큰(일회성)
    email_verification_token = models.UUIDField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()