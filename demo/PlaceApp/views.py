from django.db.models import F, Max
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from .models import (
    TravelPlace,
    HotSpot,
    TrendSpot,
    Wishlist,
    WishlistItem,
    TravelPlaceLike,
)
from .serializers import (
    TravelPlaceSerializer,
    HotSpotSerializer,
    TrendSpotSerializer,
    WishlistSerializer,
    WishlistItemSerializer,
)


# ------------------------
# TravelPlace (여행지 마스터)
# ------------------------
class TravelPlaceListCreateView(generics.ListCreateAPIView):
    """
    GET  /place/places/           : 여행지 목록 (검색/지역 필터)
    POST /place/places/           : 여행지 생성 (관리자만)
    """

    queryset = TravelPlace.objects.all()
    serializer_class = TravelPlaceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "country", "state", "city", "district"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()

        params = self.request.query_params
        country = params.get("country")
        state = params.get("state")
        city = params.get("city")
        district = params.get("district")

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

        TravelPlace.objects.filter(pk=instance.pk).update(
            view_count=F("view_count") + 1
        )
        instance.refresh_from_db(fields=["view_count"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ------------------------
# 좋아요 (TravelPlaceLike)
# ------------------------
class TravelPlaceLikeView(APIView):
    """
    POST   /place/places/<pk>/like/   : 좋아요 누르기 (idempotent)
    DELETE /place/places/<pk>/like/   : 좋아요 취소
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        place = get_object_or_404(TravelPlace, pk=pk)

        like, created = TravelPlaceLike.objects.get_or_create(
            user=request.user,
            place=place,
        )

        if created:
            TravelPlace.objects.filter(pk=place.pk).update(
                likes_count=F("likes_count") + 1
            )
            place.refresh_from_db(fields=["likes_count"])

        return Response(
            {"liked": True, "likes_count": place.likes_count},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        place = get_object_or_404(TravelPlace, pk=pk)

        deleted, _ = TravelPlaceLike.objects.filter(
            user=request.user, place=place
        ).delete()

        if deleted:
            TravelPlace.objects.filter(pk=place.pk, likes_count__gt=0).update(
                likes_count=F("likes_count") - 1
            )
            place.refresh_from_db(fields=["likes_count"])

        return Response(
            {"liked": False, "likes_count": place.likes_count},
            status=status.HTTP_200_OK,
        )


class LikedPlaceListView(generics.ListAPIView):
    """
    GET /place/likes/
    - 내가 좋아요 누른 여행지 목록
    """

    serializer_class = TravelPlaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            TravelPlace.objects.filter(likes__user=self.request.user)
            .distinct()
            .order_by("name")
        )


# ------------------------
# HotSpot (요즘 HOT한 여행지)
# ------------------------
class HotSpotListView(generics.ListAPIView):
    """
    GET /place/hotspots/
    - 가장 최근 기간(start_date) 기준 HOT 여행지
    - query params:
        - limit
        - country/state/city/district
        - start_date, end_date (직접 기간 지정 시)
    """

    serializer_class = HotSpotSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = HotSpot.objects.select_related("place")
        params = self.request.query_params

        start_date = params.get("start_date")
        end_date = params.get("end_date")
        recent_only = params.get("recent_only") in ["1", "true", "True", "yes", "on"]

        if start_date and end_date:
            qs = qs.filter(start_date__gte=start_date, end_date__lte=end_date)
        elif recent_only:
            latest = qs.aggregate(latest_start=Max("start_date"))["latest_start"]
            if latest:
                qs = qs.filter(start_date=latest)

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


# ------------------------
# TrendSpot (나이대별 트렌드)
# ------------------------
class TrendSpotListView(generics.ListAPIView):
    """
    GET /place/trendspots/
    - 나이대별 Trend 여행지
    - query params:
        - age_group (기본 GLOBAL)
        - limit
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
        recent_only = params.get("recent_only") in ["1", "true", "True", "yes", "on"]

        if start_date and end_date:
            qs = qs.filter(start_date__gte=start_date, end_date__lte=end_date)
        elif recent_only:
            latest = qs.aggregate(latest_start=Max("start_date"))["latest_start"]
            if latest:
                qs = qs.filter(start_date=latest)

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


# ------------------------
# Wishlist (폴더)
# ------------------------
class WishlistListCreateView(generics.ListCreateAPIView):
    """
    GET  /place/wishlists/           : 내가 만든 모든 위시리스트
    POST /place/wishlists/           : 새 위시리스트 생성
      Body:
      {
        "title": "겨울에 가고 싶은 곳",
        "description": "눈 오는 여행지 위주"
      }
    """

    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WishlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /place/wishlists/<id>/
    PATCH  /place/wishlists/<id>/
    DELETE /place/wishlists/<id>/
    """

    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)


# ------------------------
# WishlistItem (위시리스트 안 항목)
# ------------------------
class WishlistItemListCreateView(generics.ListCreateAPIView):
    """
    GET  /place/wishlists/<wishlist_id>/items/
    POST /place/wishlists/<wishlist_id>/items/
      Body 예:
      {
        "travel_spot": 3
      }
    """

    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_wishlist(self):
        return get_object_or_404(
            Wishlist,
            pk=self.kwargs["wishlist_id"],
            user=self.request.user,
        )

    def get_queryset(self):
        wishlist = self.get_wishlist()
        return (
            WishlistItem.objects.filter(wishlist=wishlist)
            .select_related("travel_spot")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["wishlist"] = self.get_wishlist()
        return ctx

    def perform_create(self, serializer):
        wishlist = self.get_wishlist()
        serializer.save(wishlist=wishlist)


class WishlistItemDetailView(generics.DestroyAPIView):
    """
    DELETE /place/wishlist-items/<id>/
    - 내 위시리스트 아이템 삭제
    """

    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 내 위시리스트 안에 있는 것만 삭제 가능
        return WishlistItem.objects.filter(wishlist__user=self.request.user)
