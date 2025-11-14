from rest_framework import serializers
from StoryApp.models import TravelStory, StoryLike, StoryComment
from PlaceApp.models import TravelPlace


class PlaceMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPlace
        fields = ("id", "name", "photo", "country", "state", "city", "district")


class StoryCreateSerializer(serializers.ModelSerializer):
    """
    글 생성용
    - 지역 필수 (country/state/city/district)
    - place(optional)
    - 지역값을 안 주고 place만 주면 place의 지역으로 채워줌
    """

    place = serializers.PrimaryKeyRelatedField(
        queryset=TravelPlace.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = TravelStory
        fields = (
            "id",
            "country",
            "state",
            "city",
            "district",
            "place",
            "title",
            "content",
            "photo_url",
            "is_public",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        place = attrs.get("place")
        # 지역이 비어 있고 place만 있으면 place의 지역으로 채움
        region_keys = ["country", "state", "city", "district"]
        if place:
            if all(not attrs.get(k) for k in region_keys):
                attrs["country"] = place.country
                attrs["state"] = place.state
                attrs["city"] = place.city
                attrs["district"] = place.district
            else:
                # 둘 다 있으면 정합성 체크(선택)
                for k in region_keys:
                    if attrs.get(k) and getattr(place, k) != attrs[k]:
                        raise serializers.ValidationError(
                            f"선택한 place의 {k} 값과 요청한 {k} 값이 다릅니다."
                        )
        # 지역 정보는 최소 country는 있어야 한다고 가정(원하면 완전 자유도 OK)
        if not attrs.get("country"):
            raise serializers.ValidationError("country는 필수입니다.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return TravelStory.objects.create(author=user, **validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = StoryComment
        fields = ("id", "user", "user_name", "content", "created_at")
        read_only_fields = ("id", "user", "user_name", "created_at")

    def get_user_name(self, obj):
        return getattr(obj.user, "username", str(obj.user_id))


class StoryListSerializer(serializers.ModelSerializer):
    place = PlaceMiniSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = TravelStory
        fields = (
            "id",
            "author",
            "author_name",
            "country",
            "state",
            "city",
            "district",
            "place",
            "title",
            "preview",
            "photo_url",
            "liked_count",
            "view_count",
            "created_at",
        )
        read_only_fields = fields

    def get_author_name(self, obj):
        return getattr(obj.author, "username", str(obj.author_id))

    def get_preview(self, obj):
        return (obj.content or "")[:120]


class StoryDetailSerializer(serializers.ModelSerializer):
    place = PlaceMiniSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = TravelStory
        fields = (
            "id",
            "author",
            "author_name",
            "country",
            "state",
            "city",
            "district",
            "place",
            "title",
            "content",
            "photo_url",
            "is_public",
            "liked_count",
            "view_count",
            "created_at",
            "updated_at",
            "comments",
        )
        read_only_fields = fields

    def get_author_name(self, obj):
        return getattr(obj.author, "username", str(obj.author_id))
