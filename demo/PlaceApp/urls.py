from django.urls import path

from .views import (
    TravelPlaceListCreateView,
    TravelPlaceCreateByLocalView,
    TravelPlaceDetailView,
    TravelPlaceLikeView,
    LikedPlaceListView,
    HotSpotListView,
    TrendSpotListView,
    WishlistListCreateView,
    WishlistDetailView,
    WishlistItemListCreateView,
    WishlistItemDetailView,
    CountryHotRankingView,
    CityHotRankingView,
    PlacesByRegionView,
)

urlpatterns = [
    # 여행지 마스터
    path("places/", TravelPlaceListCreateView.as_view()),
    path("places/create-by-local/", TravelPlaceCreateByLocalView.as_view()),
    path("places/<int:pk>/", TravelPlaceDetailView.as_view()),
    path("places/by-region/", PlacesByRegionView.as_view()),
    # 좋아요
    path("places/<int:pk>/like/", TravelPlaceLikeView.as_view()),
    path("likes/", LikedPlaceListView.as_view()),
    # HOT / Trend
    path("hotspots/", HotSpotListView.as_view()),
    path("hotspots/countries/", CountryHotRankingView.as_view()),
    path("hotspots/cities/", CityHotRankingView.as_view()),
    path("trendspots/", TrendSpotListView.as_view()),
    # 위시리스트 (폴더)
    path("wishlists/", WishlistListCreateView.as_view()),
    path("wishlists/<int:pk>/", WishlistDetailView.as_view()),
    # 위시리스트 아이템
    path("wishlists/<int:wishlist_id>/items/", WishlistItemListCreateView.as_view()),
    path("wishlist-items/<int:pk>/", WishlistItemDetailView.as_view()),
]
