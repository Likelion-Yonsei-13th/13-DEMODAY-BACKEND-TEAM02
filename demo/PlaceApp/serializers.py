from rest_framework import serializers
from .models import TravelPlace, HotSpot, TrendSpot


class TravelPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPlace
        fields = [
            "id",
            "name",
            "photo",
            "country",
            "state",
            "city",
            "district",
            "view_count",
        ]


class HotSpotSerializer(serializers.ModelSerializer):
    # 카드에 여행지 정보까지 같이 필요하니까 nested 로 내려줌
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
