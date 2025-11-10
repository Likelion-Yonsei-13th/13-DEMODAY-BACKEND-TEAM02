from django.conf import settings
from django.db import models
from django.utils import timezone


class TravelPlace(models.Model):
    """
    여행지 마스터
    """

    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=50)
    photo = models.URLField(max_length=255)

    # 위치 정보 (나라 / 시도 / 구 / 동)
    country = models.CharField(max_length=50, default="", blank=True)
    state = models.CharField(max_length=50, default="", blank=True)
    city = models.CharField(max_length=50, default="", blank=True)
    district = models.CharField(max_length=50, default="", blank=True)

    # 조회수 / 좋아요 수
    view_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "travel_place"
        indexes = [
            models.Index(fields=["country", "state", "city", "district"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.country}/{self.state}/{self.city}/{self.district})"


class TravelPlaceLike(models.Model):
    """
    여행지 좋아요(하트)
    - 유저당 하나만
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_likes",
    )
    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "travelplace_like"
        unique_together = ("user", "place")

    def __str__(self):
        return f"{self.user_id} ♥ {self.place_id}"


class HotSpot(models.Model):
    """
    기간별 HOT 여행지 (랭킹 캐시)
    """

    hot_id = models.BigAutoField(primary_key=True)

    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="hotspots",
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    score = models.DecimalField(max_digits=10, decimal_places=4)
    rank = models.PositiveIntegerField()

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hot_spot"
        indexes = [
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["rank"]),
        ]
        unique_together = ("place", "start_date", "end_date")

    def __str__(self):
        return f"HotSpot#{self.hot_id} place={self.place_id} rank={self.rank}"


class TrendSpot(models.Model):
    """
    나이대별 Trend 여행지 (랭킹 캐시)
    """

    class AgeGroup(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        AGE_10S = "10S", "10대"
        AGE_20S = "20S", "20대"
        AGE_30S = "30S", "30대"
        AGE_40S = "40S", "40대"
        AGE_50S = "50S", "50대"
        AGE_60P = "60P", "60+"
        UNKNOWN = "UNKNOWN", "Unknown"

    trend_id = models.BigAutoField(primary_key=True)

    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="trendspots",
    )

    age_group = models.CharField(
        max_length=10,
        choices=AgeGroup.choices,
        default=AgeGroup.GLOBAL,
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    score = models.DecimalField(max_digits=10, decimal_places=4)
    rank = models.PositiveIntegerField()

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "trend_spot"
        indexes = [
            models.Index(fields=["age_group", "start_date", "end_date"]),
            models.Index(fields=["rank"]),
        ]
        unique_together = ("place", "age_group", "start_date", "end_date")

    def __str__(self):
        return f"TrendSpot#{self.trend_id} place={self.place_id} age={self.age_group} rank={self.rank}"


class Wishlist(models.Model):
    """
    유저가 만드는 '위시리스트 폴더'
    - 유튜브 플레이리스트 같은 개념
    """

    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlists",
    )
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlist"

    def __str__(self):
        return f"{self.user_id} - {self.title}"


class WishlistItem(models.Model):
    """
    위시리스트 안에 실제로 담기는 아이템
    - 지금은 여행지(TravelPlace)와 트렌드 카드(TrendSpot)만 연결
    """

    id = models.BigAutoField(primary_key=True)

    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )

    travel_spot = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        null=True,
        blank=True,
    )

    trend = models.ForeignKey(
        TrendSpot,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlist_item"
        unique_together = ("wishlist", "travel_spot", "trend")

    def __str__(self):
        return f"WishlistItem#{self.id} wishlist={self.wishlist_id}"
