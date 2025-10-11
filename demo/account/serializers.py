from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('nickname', 'email', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    nickname = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        nickname = data.get('nickname')
        password = data.get('password')

        try:
            user = User.objects.get(nickname=nickname)
        except User.DoesNotExist:
            raise serializers.ValidationError("아이디 또는 비밀번호가 일치하지 않습니다.")

        if not user.is_active:
            raise serializers.ValidationError("이메일 인증이 완료되지 않았습니다.")

        if not check_password(password, user.password):
            raise serializers.ValidationError("아이디 또는 비밀번호가 일치하지 않습니다.")

        data['user'] = user
        return data