from rest_framework import serializers

from .models import (
    TravelPlace,
    HotSpot,
    TrendSpot,
    Wishlist,
    WishlistItem,
)


class TravelPlaceSerializer(serializers.ModelSerializer):
    photo_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    photo = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TravelPlace
        fields = [
            "id",
            "name",
            "photo",
            "photo_url",
            "country",
            "state",
            "city",
            "district",
            "view_count",
            "likes_count",
        ]
    
    def get_photo(self, obj):
        # photo_url이 있으면 우선 반환
        if obj.photo_url:
            return obj.photo_url
        
        # photo ImageField가 있으면 반환
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        
        return ""
    
    def create(self, validated_data):
        photo_url = validated_data.pop('photo_url', None)
        
        # photo_url을 모델의 photo_url 필드에 저장
        if photo_url:
            validated_data['photo_url'] = photo_url
        
        instance = super().create(validated_data)
        return instance


class TravelPlaceListSerializerFlat(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = TravelPlace
        fields = (
            "id",
            "name",
            "photo",
            "country",
            "state",
            "city",
            "district",
            "likes_count",
            "view_count",
        )
    
    def get_photo(self, obj):
        # photo_url이 있으면 우선 반환
        if obj.photo_url:
            return obj.photo_url
        
        # photo ImageField가 있으면 반환
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        
        return ""


class HotSpotSerializer(serializers.ModelSerializer):
    place = TravelPlaceSerializer(read_only=True)

    class Meta:
        model = HotSpot
        fields = [
            "hot_id",
            "place",
            "start_date",
            "end_date",
            "score",
            "rank",
        ]


class TrendSpotSerializer(serializers.ModelSerializer):
    place = TravelPlaceSerializer(read_only=True)

    class Meta:
        model = TrendSpot
        fields = [
            "trend_id",
            "place",
            "age_group",
            "start_date",
            "end_date",
            "score",
            "rank",
        ]


class WishlistItemSerializer(serializers.ModelSerializer):
    travel_spot_detail = TravelPlaceSerializer(source="travel_spot", read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "id",
            "travel_spot",
            "trend",
            "created_at",
            "travel_spot_detail",
        ]
        read_only_fields = ["id", "created_at", "travel_spot_detail"]

    def validate(self, attrs):
        """
        - travel_spot 또는 trend 중 하나는 있어야 함
        - 같은 wishlist 안에 같은 항목 중복 추가 방지
        """
        request = self.context.get("request")
        wishlist = self.context.get("wishlist")

        travel_spot = attrs.get("travel_spot")
        trend = attrs.get("trend")

        if not wishlist:
            raise serializers.ValidationError("Wishlist 정보가 필요합니다.")

        if not (travel_spot or trend):
            raise serializers.ValidationError(
                "travel_spot 또는 trend 중 하나는 반드시 필요합니다."
            )

        if WishlistItem.objects.filter(
            wishlist=wishlist,
            travel_spot=travel_spot,
            trend=trend,
        ).exists():
            raise serializers.ValidationError("이미 이 위시리스트에 추가된 항목입니다.")

        return attrs


class WishlistSerializer(serializers.ModelSerializer):
    # 위시리스트 상세 조회 시, 안에 항목까지 같이 보고 싶을 때 사용
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = [
            "id",
            "title",
            "description",
            "is_public",
            "created_at",
            "items",
        ]
        read_only_fields = ["id", "created_at", "items"]
