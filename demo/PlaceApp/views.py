from django.db.models import F, Max
from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from .models import TravelPlace, HotSpot, TrendSpot
from .serializers import (
    TravelPlaceSerializer,
    HotSpotSerializer,
    TrendSpotSerializer,
)


# ------------------------
# TravelPlace (여행지 마스터)
# ------------------------
class TravelPlaceListCreateView(generics.ListCreateAPIView):
    """
    GET  /place/places/            : 여행지 목록 (검색/필터)
    POST /place/places/            : 여행지 생성 (관리자용)
    """

    queryset = TravelPlace.objects.all()
    serializer_class = TravelPlaceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "country", "state", "city", "district"]

    def get_permissions(self):
        # 리스트 조회는 모두 허용, 생성은 관리자만
        if self.request.method == "POST":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()

        # 나라/시도/구/동 필터
        country = self.request.query_params.get("country")
        state = self.request.query_params.get("state")
        city = self.request.query_params.get("city")
        district = self.request.query_params.get("district")

        if country:
            qs = qs.filter(country=country)
        if state:
            qs = qs.filter(state=state)
        if city:
            qs = qs.filter(city=city)
        if district:
            qs = qs.filter(district=district)

        return qs.order_by("name")


class TravelPlaceDetailView(generics.RetrieveAPIView):
    """
    GET /place/places/<pk>/
    - 상세 조회 + view_count 자동 증가
    """

    queryset = TravelPlace.objects.all()
    serializer_class = TravelPlaceSerializer
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # view_count += 1 (race condition 줄이려고 F() 사용)
        TravelPlace.objects.filter(pk=instance.pk).update(
            view_count=F("view_count") + 1
        )
        instance.refresh_from_db(fields=["view_count"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ------------------------
# HotSpot (요즘 HOT한 여행지)
# ------------------------
class HotSpotListView(generics.ListAPIView):
    """
    GET /place/hotspots/
    - 요즘 HOT한 여행지 리스트
    - 기본: 가장 최근 start_date 기간의 랭킹을 rank 순으로 반환
    - query params:
        - limit: 개수 제한 (기본 10)
        - country/state/city/district: 지역 필터
        - start_date, end_date(선택): 특정 기간 강제 지정
    """

    serializer_class = HotSpotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = HotSpot.objects.select_related("place")

        # 기간 필터 (없으면 가장 최근 start_date 한 번만 사용)
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if not (start_date and end_date):
            latest = qs.aggregate(latest_start=Max("start_date"))["latest_start"]
            if latest:
                qs = qs.filter(start_date=latest)
        else:
            qs = qs.filter(start_date=start_date, end_date=end_date)

        # 위치 필터는 place 를 통해
        params = self.request.query_params
        country = params.get("country")
        state = params.get("state")
        city = params.get("city")
        district = params.get("district")

        if country:
            qs = qs.filter(place__country=country)
        if state:
            qs = qs.filter(place__state=state)
        if city:
            qs = qs.filter(place__city=city)
        if district:
            qs = qs.filter(place__district=district)

        qs = qs.order_by("rank", "-score")

        # limit
        try:
            limit = int(self.request.query_params.get("limit", "10"))
        except ValueError:
            limit = 10
        return qs[:limit]


# ------------------------
# TrendSpot (나이대별 Trend 여행지)
# ------------------------
class TrendSpotListView(generics.ListAPIView):
    """
    GET /place/trendspots/
    - 나이대별 Trend 여행지 리스트
    - 기본: age_group=GLOBAL + 가장 최근 start_date 기준
    - query params:
        - age_group: GLOBAL, 10S, 20S, 30S, 40S, 50S, 60P, UNKNOWN
        - limit: 개수 (기본 10)
        - country/state/city/district
        - start_date, end_date
    """

    serializer_class = TrendSpotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = TrendSpot.objects.select_related("place")

        params = self.request.query_params
        age_group = params.get("age_group", "GLOBAL")
        qs = qs.filter(age_group=age_group)

        start_date = params.get("start_date")
        end_date = params.get("end_date")

        if not (start_date and end_date):
            latest = qs.aggregate(latest_start=Max("start_date"))["latest_start"]
            if latest:
                qs = qs.filter(start_date=latest)
        else:
            qs = qs.filter(start_date=start_date, end_date=end_date)

        country = params.get("country")
        state = params.get("state")
        city = params.get("city")
        district = params.get("district")

        if country:
            qs = qs.filter(place__country=country)
        if state:
            qs = qs.filter(place__state=state)
        if city:
            qs = qs.filter(place__city=city)
        if district:
            qs = qs.filter(place__district=district)

        qs = qs.order_by("rank", "-score")

        try:
            limit = int(params.get("limit", "10"))
        except ValueError:
            limit = 10
        return qs[:limit]
