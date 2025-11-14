from django.contrib import admin
from StoryApp.models import TravelStory, StoryLike, StoryComment


@admin.register(TravelStory)
class TravelStoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "country",
        "state",
        "city",
        "district",
        "liked_count",
        "view_count",
        "created_at",
    )
    list_filter = ("country", "state", "city", "district", "is_public")
    search_fields = ("title", "content")


@admin.register(StoryLike)
class StoryLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "story", "user", "created_at")
    list_filter = ("created_at",)


@admin.register(StoryComment)
class StoryCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "story", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content",)
