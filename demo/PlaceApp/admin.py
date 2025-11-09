from django.contrib import admin
from .models import (
    TravelPlace,
    HotSpot,
    TrendSpot,
    Wishlist,
    WishlistItem,
    TravelPlaceLike,
)


@admin.register(TravelPlace)
class TravelPlaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "country",
        "state",
        "city",
        "view_count",
        "likes_count",
    )
    list_filter = ("country", "state", "city")
    search_fields = ("name", "country", "state", "city", "district")


@admin.register(HotSpot)
class HotSpotAdmin(admin.ModelAdmin):
    list_display = ("hot_id", "place", "start_date", "end_date", "score", "rank")
    list_filter = ("start_date", "end_date")
    search_fields = ("place__name",)


@admin.register(TrendSpot)
class TrendSpotAdmin(admin.ModelAdmin):
    list_display = (
        "trend_id",
        "place",
        "age_group",
        "start_date",
        "end_date",
        "score",
        "rank",
    )
    list_filter = ("age_group", "start_date", "end_date")
    search_fields = ("place__name",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_public", "created_at")
    search_fields = ("title", "user__username", "user__email")
    list_filter = ("is_public", "created_at")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "wishlist", "travel_spot", "trend", "created_at")
    search_fields = (
        "wishlist__title",
        "wishlist__user__username",
        "travel_spot__name",
        "trend__place__name",
    )
    list_filter = ("created_at",)


@admin.register(TravelPlaceLike)
class TravelPlaceLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "place", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "place__name",
    )
    list_filter = ("created_at",)
