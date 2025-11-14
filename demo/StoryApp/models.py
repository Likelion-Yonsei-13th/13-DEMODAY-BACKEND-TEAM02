from django.conf import settings
from django.db import models
from django.db.models import F
from PlaceApp.models import TravelPlace  # 선택적으로 연결


class TravelStory(models.Model):
    """
    지역(필수) + 장소(선택) 기반의 여행 후기 글
    - 드릴다운으로 받은 country/state/city/district 를 항상 저장
    - place(선택): 사용자가 특정 장소까지 지정했을 때만 연결
    """

    id = models.BigAutoField(primary_key=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
    )

    # 지역 정보 (드릴다운)
    country = models.CharField(max_length=50, default="", blank=True, db_index=True)
    state = models.CharField(max_length=50, default="", blank=True, db_index=True)
    city = models.CharField(max_length=50, default="", blank=True, db_index=True)
    district = models.CharField(max_length=50, default="", blank=True, db_index=True)

    # 선택: 특정 장소까지 지정했다면 연결 (없어도 됨)
    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
    )

    # 본문
    title = models.CharField(max_length=50)
    content = models.TextField()  # 512 이상도 고려해서 TextField
    photo_url = models.URLField(max_length=255, blank=True, default="")
    is_public = models.BooleanField(default=True)

    # 카운터
    liked_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "travel_story"
        indexes = [
            models.Index(fields=["country", "state", "city", "district", "created_at"]),
            models.Index(fields=["liked_count"]),
            models.Index(fields=["view_count"]),
        ]

    def __str__(self):
        return f"[{self.country}/{self.state}/{self.city}/{self.district}] {self.title}"


class StoryLike(models.Model):
    """
    좋아요 관계: 한 유저가 같은 글에 한 번만.
    """

    id = models.BigAutoField(primary_key=True)
    story = models.ForeignKey(
        TravelStory, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="story_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_like"
        unique_together = ("story", "user")
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["story", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.story_id}"


class StoryComment(models.Model):
    """
    간단 댓글(1-depth). 필요하면 parent로 대댓글 확장 가능.
    """

    id = models.BigAutoField(primary_key=True)
    story = models.ForeignKey(
        TravelStory, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="story_comments",
    )
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_comment"
        indexes = [
            models.Index(fields=["story", "created_at"]),
        ]

    def __str__(self):
        return f"C{self.id} on S{self.story_id}"
