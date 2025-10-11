from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

# ✅ 커스텀 유저 매니저
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


# ✅ 커스텀 유저 모델
class User(AbstractUser):
    username = None  # username 필드 제거
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=False)  # 이메일 인증 후 활성화
    email_verification_token = models.UUIDField(null=True, blank=True)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email