from django.contrib import admin
from .models import TravelPlace, HotSpot, TrendSpot

@admin.register(TravelPlace)
class TravelPlaceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "view_count")
    search_fields = ("name",)

@admin.register(HotSpot)
class HotSpotAdmin(admin.ModelAdmin):
    list_display = ("hot_id", "place", "start_date", "end_date", "score", "rank")
    list_filter = ("start_date", "end_date")
    search_fields = ("place__name",)

@admin.register(TrendSpot)
class TrendSpotAdmin(admin.ModelAdmin):
    list_display = ("trend_id", "place", "age_group", "start_date", "end_date", "score", "rank")
    list_filter = ("age_group", "start_date", "end_date")
    search_fields = ("place__name",)
