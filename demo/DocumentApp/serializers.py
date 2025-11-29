from rest_framework import serializers
from .models import Request, Root, ThemeTag, Rating
from PlaceApp.models import TravelPlace


# -------- TravelPlace (여행지 정보) --------
class TravelPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPlace
        fields = ["id", "name", "country", "state", "city", "district"]
        read_only_fields = ["id"]


# -------- ThemeTag (공통 태그 표현용) --------
class ThemeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeTag
        fields = ["id", "name", "level", "parent"]
        read_only_fields = ["id", "level", "parent"]


# -------- Request --------
class RequestSerializer(serializers.ModelSerializer):
    # 사용자 식별은 읽기 전용으로 uuid(pk)만 노출
    user = serializers.SerializerMethodField(read_only=True)

    # 여행지 정보 nested 반환 (GET), 작성 시는 ID만 (POST/PUT)
    place = TravelPlaceSerializer(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=TravelPlace.objects.all(),
        source="place",
        write_only=True,
    )

    # 응답용: 사용자가 선택한 모든 여행 태그 정보 (level1/2/3 포함)
    travel_type = ThemeTagSerializer(many=True, read_only=True)

    # 요청용: 태그 id 리스트
    travel_type_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        source="travel_type",
        queryset=ThemeTag.objects.all(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    # 응답용: 요청서에 연결된 제안서(Root) 목록
    proposals = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Request
        fields = [
            "id",
            "user",
            "place",
            "place_id",
            "title",
            "date",
            "end_date",
            "number_of_people",
            "guidance",
            "travel_type",
            "travel_type_ids",
            "experience",
            "is_public_profile",
            "created_at",
            "proposals",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def get_user(self, obj):
        # 프로필에서 photo_url 가져오기
        photo_url = ""
        if hasattr(obj.user, 'userprofile') and obj.user.userprofile.photo_url:
            photo_url = obj.user.userprofile.photo_url
        
        return {
            "uuid": str(obj.user_id),
            "display_name": obj.user.display_name or "",
            "photo_url": photo_url,
        }

    def get_proposals(self, obj):
        # 요청서에 연결된 모든 제안서(Root) 반환
        # prefetch_related로 대랙 차기된 데이터 사용
        proposal_maps = list(obj.proposals.all())
        return [
            {
                "id": proposal_map.root.id,
                "title": proposal_map.root.title,
                "founder": {
                    "uuid": str(proposal_map.root.founder_id),
                    "display_name": proposal_map.root.founder.display_name or "",
                },
                "created_at": proposal_map.created_at,
            }
            for proposal_map in proposal_maps
        ]

    def validate_number_of_people(self, v):
        if v < 1:
            raise serializers.ValidationError("number_of_people는 1 이상이어야 합니다.")
        return v

    def create(self, validated_data):
        # travel_type (ManyToMany) 를 분리해서 처리
        tags = validated_data.pop("travel_type", [])
        validated_data["user"] = self.context["request"].user
        instance = super().create(validated_data)
        if tags:
            instance.travel_type.set(tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("travel_type", None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.travel_type.set(tags)
        return instance


# -------- Root --------
class RootSerializer(serializers.ModelSerializer):
    founder = serializers.SerializerMethodField(read_only=True)

    # 여행지 정보 nested 반환 (GET), 작성 시는 ID만 (POST/PUT)
    place = TravelPlaceSerializer(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=TravelPlace.objects.all(),
        source="place",
        write_only=True,
    )
    
    # photo는 이미 업로드된 이미지 URL 문자열로 받음
    photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # 응답용: 루트에 연결된 모든 여행 태그 정보
    travel_type = ThemeTagSerializer(many=True, read_only=True)

    # 요청용: 태그 id 리스트
    travel_type_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        source="travel_type",
        queryset=ThemeTag.objects.all(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Root
        fields = [
            "id",
            "founder",
            "place",
            "place_id",
            "title",
            "photo",
            "schedule",
            "number_of_people",
            "guidance",
            "travel_type",
            "travel_type_ids",
            "experience",
            "average_rating",
            "rating_count",
            "created_at",
            "modified_at",
        ]
        read_only_fields = ["id", "founder", "average_rating", "rating_count", "created_at", "modified_at"]

    def get_founder(self, obj):
        # 프로필에서 photo_url 가져오기
        photo_url = ""
        if hasattr(obj.founder, 'localprofile') and obj.founder.localprofile.photo_url:
            photo_url = obj.founder.localprofile.photo_url
        
        return {
            "uuid": str(obj.founder_id),
            "display_name": obj.founder.display_name or "",
            "photo_url": photo_url,
        }

    def validate_number_of_people(self, v):
        if v < 1:
            raise serializers.ValidationError("number_of_people는 1 이상이어야 합니다.")
        return v

    def create(self, validated_data):
        tags = validated_data.pop("travel_type", [])
        validated_data["founder"] = self.context["request"].user
        instance = super().create(validated_data)
        if tags:
            instance.travel_type.set(tags)
        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("travel_type", None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.travel_type.set(tags)
        return instance


# -------- Rating --------
class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ["id", "root", "user", "rating", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        # 로그인 사용자를 user로 설정 (비로그인 허용 시 None)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user
        else:
            validated_data["user"] = None
        return super().create(validated_data)
