from django.db import models
from django.core.validators import MinValueValidator

class TravelPlace(models.Model):
    name = models.CharField("여행지 이름", max_length=50)                       # NOT NULL
    photo = models.CharField("여행지 사진 url", max_length=255)                 # NOT NULL
    view_count = models.PositiveIntegerField("조회수", default=0)               # INT UNSIGNED, NOT NULL DEFAULT 0

    class Meta:
        db_table = "travel_place"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} (views={self.view_count})"


class HotSpot(models.Model):
    hot_id = models.BigAutoField(primary_key=True, db_column="Hot_id")
    place = models.ForeignKey(
        TravelPlace, on_delete=models.CASCADE, related_name="hotspots", db_column="place_id"
    )                                                                        # FK
    start_date = models.DateTimeField("집계 시작일")                            # NOT NULL
    end_date   = models.DateTimeField("집계 종료일")                            # NOT NULL
    score = models.DecimalField("최종 점수", max_digits=10, decimal_places=4)   # DECIMAL(10,4), NOT NULL
    rank  = models.PositiveIntegerField("순위")                                 # INT UNSIGNED, NOT NULL

    class Meta:
        db_table = "hot_spot"
        indexes = [
            models.Index(fields=["place", "start_date"]),
            models.Index(fields=["rank"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(end_date__gte=models.F("start_date")),
                                   name="hotspot_period_valid"),
        ]

    def __str__(self):
        return f"HotSpot#{self.hot_id} place={self.place_id} rank={self.rank}"


class TrendSpot(models.Model):
    class AgeGroup(models.TextChoices):
        GLOBAL = "GLOBAL", "GLOBAL"
        AGES_10 = "10S", "10S"
        AGES_20 = "20S", "20S"
        AGES_30 = "30S", "30S"
        AGES_40 = "40S", "40S"
        AGES_50 = "50S", "50S"
        AGES_60P = "60P", "60P"
        UNKNOWN = "UNKNOWN", "UNKNOWN"

    trend_id = models.BigAutoField(primary_key=True, db_column="Trend_id")
    place = models.ForeignKey(
        TravelPlace, on_delete=models.CASCADE, related_name="trendspots", db_column="place_id"
    )                                                                        # FK
    start_date = models.DateTimeField("집계 시작일")                            # NOT NULL
    end_date   = models.DateTimeField("집계 종료일")                            # NOT NULL
    score = models.DecimalField("최종 점수", max_digits=10, decimal_places=4)   # DECIMAL(10,4), NOT NULL
    rank  = models.PositiveIntegerField("순위")                                 # INT UNSIGNED, NOT NULL
    age_group = models.CharField(                                             # ENUM(...), NOT NULL DEFAULT 'GLOBAL'
        "나이대 세그먼트",
        max_length=10,
        choices=AgeGroup.choices,
        default=AgeGroup.GLOBAL,
    )

    class Meta:
        db_table = "trend_spot"
        indexes = [
            models.Index(fields=["place", "age_group", "start_date"]),
            models.Index(fields=["rank"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(end_date__gte=models.F("start_date")),
                                   name="trendspot_period_valid"),
        ]

    def __str__(self):
        return f"TrendSpot#{self.trend_id} place={self.place_id} age={self.age_group} rank={self.rank}"
