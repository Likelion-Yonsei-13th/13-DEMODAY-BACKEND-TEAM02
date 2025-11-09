from django.urls import path
from .views import (
    TravelPlaceListCreateView,
    TravelPlaceDetailView,
    HotSpotListView,
    TrendSpotListView,
)

urlpatterns = [
    # 여행지 마스터
    path("places/", TravelPlaceListCreateView.as_view()),
    path("places/<int:pk>/", TravelPlaceDetailView.as_view()),
    # 요즘 HOT한 여행지
    path("hotspots/", HotSpotListView.as_view()),
    # 나이대별 Trend 여행지
    path("trendspots/", TrendSpotListView.as_view()),
]
