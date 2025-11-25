from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core import exceptions
from django.contrib.auth.password_validation import validate_password
from .models import Interest, InstagramVerification, LocalProfile, UserProfile

User = get_user_model()


# ------------------------
# Register / Login
# ------------------------
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)
    display_name = serializers.CharField(required=False, allow_blank=True)
    birth_year = serializers.IntegerField(required=True)

    # 약관 동의 체크박스
    is_over_14 = serializers.BooleanField(required=True)
    agreed_service_terms = serializers.BooleanField(required=True)
    agreed_privacy = serializers.BooleanField(required=True)
    agreed_marketing = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password2",
            "role",
            "display_name",
            "birth_year",
            "is_over_14",
            "agreed_service_terms",
            "agreed_privacy",
            "agreed_marketing",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        try:
            validate_password(attrs["password"])
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        if not attrs.get("is_over_14"):
            raise serializers.ValidationError(
                {"is_over_14": "만 14세 이상 동의가 필요합니다."}
            )
        if not attrs.get("agreed_service_terms"):
            raise serializers.ValidationError(
                {"agreed_service_terms": "이용약관 동의는 필수입니다."}
            )
        if not attrs.get("agreed_privacy"):
            raise serializers.ValidationError(
                {"agreed_privacy": "개인정보 처리방침 동의는 필수입니다."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2", None)
        role = validated_data.pop("role")
        display_name = validated_data.pop("display_name")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,  # 이메일 인증 전까지 비활성
            role=role,
            display_name=display_name,
            birth_year=validated_data.get("birth_year"),
            is_over_14=validated_data.get("is_over_14", False),
            agreed_service_terms=validated_data.get("agreed_service_terms", False),
            agreed_privacy=validated_data.get("agreed_privacy", False),
            agreed_marketing=validated_data.get("agreed_marketing", False),
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "아이디 또는 비밀번호가 올바르지 않습니다."
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                "아이디 또는 비밀번호가 올바르지 않습니다."
            )

        if not user.is_active:
            raise serializers.ValidationError("이메일 인증이 완료되지 않았습니다.")

        data["user"] = user
        return data


# ------------------------
# Onboarding Domain
# ------------------------


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ["id", "name", "slug"]


# --- Instagram verification ---
class InstagramRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramVerification
        fields = ["handle"]

    def create(self, validated_data):
        user = self.context["request"].user
        obj, created = InstagramVerification.objects.get_or_create(
            user=user, defaults={"handle": validated_data["handle"]}
        )
        if not created:
            obj.handle = validated_data["handle"]
            obj.status = InstagramVerification.Status.PENDING
            obj.save(update_fields=["handle", "status"])
        return obj


class InstagramStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramVerification
        fields = ["handle", "code", "status", "proof_url", "verified_at"]


class InstagramConfirmSerializer(serializers.Serializer):
    proof_url = serializers.URLField(required=False, allow_blank=True)

    def create(self, validated_data):
        user = self.context["request"].user
        try:
            iv = user.instagram_verification
        except InstagramVerification.DoesNotExist:
            raise serializers.ValidationError("인증 요청이 먼저 필요합니다.")
        iv.status = InstagramVerification.Status.SUBMITTED
        if validated_data.get("proof_url"):
            iv.proof_url = validated_data["proof_url"]
        iv.save(update_fields=["status", "proof_url"])
        return iv


# --- Profiles ---
class LocalProfileSerializer(serializers.ModelSerializer):
    interests = serializers.SlugRelatedField(
        slug_field="slug", many=True, queryset=Interest.objects.all(), required=False
    )
    display_name = serializers.CharField(
        source="user.display_name",
        required=False,
    )

    class Meta:
        model = LocalProfile
        fields = [
            "display_name",
            "photo_url",
            "bio",
            "languages",
            "interests",
            "regions",
            "strengths",
            "portfolio",
        ]

    def create(self, validated_data):
        interests = validated_data.pop("interests", [])
        user = self.context["request"].user
        user_data = validated_data.pop("user", {})
        display_name = user_data.get("display_name")
        if display_name is not None and user.display_name != display_name:
            user.display_name = display_name
            user.save(update_fields=["display_name"])
        obj, created = LocalProfile.objects.get_or_create(
            user=user, defaults=validated_data
        )
        if not created:
            for k, v in validated_data.items():
                setattr(obj, k, v)
            obj.save()
        if interests:
            obj.interests.set(interests)
        return obj

    def update(self, instance, validated_data):
        interests = validated_data.pop("interests", None)
        user_data = validated_data.pop("user", {})
        display_name = user_data.get("display_name")
        if display_name is not None and instance.user.display_name != display_name:
            instance.user.display_name = display_name
            instance.user.save(update_fields=["display_name"])
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if interests is not None:
            instance.interests.set(interests)
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(
        source="user.display_name",
        required=False,
    )
    interests = serializers.SlugRelatedField(
        slug_field="slug", many=True, queryset=Interest.objects.all(), required=False
    )

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "photo_url",
            "bio",
            "languages",
            "interests",
            "mbti",
            "travel_style",
        ]

    def create(self, validated_data):
        interests = validated_data.pop("interests", [])
        user = self.context["request"].user
        user_data = validated_data.pop("user", {})
        display_name = user_data.get("display_name")
        if display_name is not None and user.display_name != display_name:
            user.display_name = display_name
            user.save(update_fields=["display_name"])
        obj, created = UserProfile.objects.get_or_create(
            user=user, defaults=validated_data
        )
        if not created:
            for k, v in validated_data.items():
                setattr(obj, k, v)
            obj.save()
        if interests:
            obj.interests.set(interests)
        return obj

    def update(self, instance, validated_data):
        interests = validated_data.pop("interests", None)
        user_data = validated_data.pop("user", {})
        display_name = user_data.get("display_name")
        if display_name is not None and instance.user.display_name != display_name:
            instance.user.display_name = display_name
            instance.user.save(update_fields=["display_name"])
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if interests is not None:
            instance.interests.set(interests)
        return instance
