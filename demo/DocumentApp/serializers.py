from rest_framework import serializers
from .models import Request, Root, ThemeTag


# -------- ThemeTag (for read-only exposure) --------
class ThemeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeTag
        fields = ["id", "name", "level", "parent"]
        read_only_fields = ["id", "level", "parent"]


# -------- Request --------
class RequestSerializer(serializers.ModelSerializer):
    # 사용자 식별은 읽기 전용으로 uuid(pk)만 노출
    user = serializers.SerializerMethodField(read_only=True)

    # 응답용: 선택된 모든 태그 정보 (level1/2/3 포함)
    travel_type = ThemeTagSerializer(many=True, read_only=True)

    # 요청용: 태그 id 리스트 (level1/2/3 전부 포함해서 보내면 됨)
    # ex) [ level1("여유로운"), level2("산책이 있는"), level3("강변 산책") ]
    travel_type_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        source="travel_type",          # 실제 모델 필드명
        queryset=ThemeTag.objects.all(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Request
        fields = [
            "id",
            "user",
            "place",
            "date",
            "number_of_people",
            "guidance",
            "travel_type",      # read-only (ThemeTagSerializer[])
            "travel_type_ids",  # write-only (id list)
            "experience",
            "is_public_profile",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def get_user(self, obj):
        # 커스텀 User PK는 uuid → obj.user_id가 uuid 값
        return {"uuid": str(obj.user_id)}

    def validate_number_of_people(self, v):
        if v < 1:
            raise serializers.ValidationError("number_of_people는 1 이상이어야 합니다.")
        return v

    def create(self, validated_data):
        # 생성자는 항상 현재 로그인한 USER
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# -------- Root --------
class RootSerializer(serializers.ModelSerializer):
    founder = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Root
        fields = [
            "id",
            "founder",
            "place",
            "number_of_people",
            "guidance",
            "travel_type",
            "experience",
            "created_at",
            "modified_at",
        ]
        read_only_fields = ["id", "founder", "created_at", "modified_at"]

    def get_founder(self, obj):
        return {"uuid": str(obj.founder_id)}

    def validate_number_of_people(self, v):
        if v < 1:
            raise serializers.ValidationError("number_of_people는 1 이상이어야 합니다.")
        return v

    def create(self, validated_data):
        validated_data["founder"] = self.context["request"].user
        return super().create(validated_data)
