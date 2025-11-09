from django.db import models
from django.utils import timezone


class TravelPlace(models.Model):
    """
    여행지 마스터 테이블
    - ERD: id, name, photo, view_count
    - + 위치 정보: country, state(시/도), city(구), district(동)
    """

    id = models.BigAutoField(primary_key=True)  # PK

    name = models.CharField(max_length=50)  # NOT NULL
    photo = models.URLField(max_length=255)  # NOT NULL

    # 위치 정보 (나라 / 시도 / 구 / 동)
    country = models.CharField(max_length=50)  # 예: "KR"
    state = models.CharField(max_length=50)  # 예: "서울특별시"
    city = models.CharField(max_length=50)  # 예: "마포구"
    district = models.CharField(max_length=50)  # 예: "서교동"

    view_count = models.PositiveIntegerField(default=0)  # NOT NULL, DEFAULT 0

    class Meta:
        db_table = "travel_place"
        indexes = [
            models.Index(fields=["country", "state", "city", "district"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.country}/{self.state}/{self.city}/{self.district})"


class HotSpot(models.Model):
    """
    기간별 HOT 여행지
    - 한 기간(start_date~end_date) 동안의 인기 점수/순위
    """

    hot_id = models.BigAutoField(primary_key=True)  # PK

    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="hotspots",
    )  # FK

    start_date = models.DateTimeField()  # NOT NULL
    end_date = models.DateTimeField()  # NOT NULL

    score = models.DecimalField(max_digits=10, decimal_places=4)  # NOT NULL
    rank = models.PositiveIntegerField()  # NOT NULL

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hot_spot"
        indexes = [
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["rank"]),
        ]
        # 같은 기간 안에서 같은 place 에 대해 한 줄만 유지
        unique_together = ("place", "start_date", "end_date")

    def __str__(self):
        return f"HotSpot#{self.hot_id} place={self.place_id} rank={self.rank}"


class TrendSpot(models.Model):
    """
    나이대별 Trend 여행지
    - age_group + 기간(start_date~end_date) 기준 랭킹
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

    trend_id = models.BigAutoField(primary_key=True)  # PK

    place = models.ForeignKey(
        TravelPlace,
        on_delete=models.CASCADE,
        related_name="trendspots",
    )  # FK

    age_group = models.CharField(
        max_length=10,
        choices=AgeGroup.choices,
        default=AgeGroup.GLOBAL,
    )  # NOT NULL DEFAULT 'GLOBAL'

    start_date = models.DateTimeField()  # NOT NULL
    end_date = models.DateTimeField()  # NOT NULL

    score = models.DecimalField(max_digits=10, decimal_places=4)  # NOT NULL
    rank = models.PositiveIntegerField()  # NOT NULL

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
