# PlaceApp/management/commands/recalc_hot_trend.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

from PlaceApp.models import (
    TravelPlace,
    TravelPlaceLike,
    WishlistItem,
    HotSpot,
    TrendSpot,
)
from account.models import User


class Command(BaseCommand):
    """
    최근 월 / 지정한 월 기준으로 HotSpot & TrendSpot 랭킹 생성

    사용 예시:
      # 이번 달 기준 (기본값)
      python manage.py recalc_hot_trend

      # 2025년 11월 기준
      python manage.py recalc_hot_trend --year=2025 --month=11
    """

    help = "HotSpot / TrendSpot 랭킹 재계산"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            help="집계 기준 연도 (예: 2025). 기본: 오늘 날짜 기준 연도",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="집계 기준 월 (1~12). 기본: 오늘 날짜 기준 월",
        )

    def handle(self, *args, **options):
        # 1) 기준 기간(start, end) 계산
        now = timezone.now()

        year = options["year"] or now.year
        month = options["month"] or now.month

        # 해당 월의 1일 00:00:00
        month_start_naive = datetime(year, month, 1, 0, 0, 0)

        # 해당 월의 마지막 날
        last_day = calendar.monthrange(year, month)[1]
        month_end_naive = datetime(year, month, last_day, 23, 59, 59)

        # 타임존 aware 로 변환
        start = timezone.make_aware(month_start_naive, timezone.get_current_timezone())
        end = timezone.make_aware(month_end_naive, timezone.get_current_timezone())

        self.stdout.write(self.style.NOTICE(f"[집계 기간] {start} ~ {end}"))

        # 2) 기존에 같은 기간으로 생성된 랭킹 삭제 (있으면 덮어쓰기)
        HotSpot.objects.filter(start_date=start, end_date=end).delete()
        TrendSpot.objects.filter(start_date=start, end_date=end).delete()

        # 3) 전체 기준 HotSpot 점수 계산
        place_scores = self._calc_place_scores(start, end)

        ranked_places = sorted(place_scores.items(), key=lambda x: x[1], reverse=True)

        self._create_hotspots(ranked_places, start, end)

        # 4) 나이대별 TrendSpot 계산
        self._create_trendspots(start, end)

        self.stdout.write(self.style.SUCCESS("✅ HotSpot / TrendSpot 재계산 완료"))

    # =========================
    #   내부 헬퍼 메서드들
    # =========================

    def _calc_place_scores(self, start, end):
        """
        전체 유저 기준 여행지별 점수 계산

        현재 점수 식 (나중에 가중치는 바꿔도 됨):
          score = view_count
                  + like_count_기간 * 3
                  + wishlist_count_기간 * 5
        """
        scores = {}

        for place in TravelPlace.objects.all():
            # 누적 조회수
            views = place.view_count

            # 기간 내 좋아요 수
            likes = TravelPlaceLike.objects.filter(
                place=place,
                created_at__range=(start, end),
            ).count()

            # 기간 내 위시리스트 추가 수
            wishlist_adds = WishlistItem.objects.filter(
                travel_spot=place,
                created_at__range=(start, end),
            ).count()

            score = views + likes * 3 + wishlist_adds * 5

            if score > 0:
                scores[place] = score

        return scores

    def _create_hotspots(self, ranked_places, start, end, max_count=50):
        """
        ranked_places: [(place, score), ...]
        """
        objs = []
        for idx, (place, score) in enumerate(ranked_places[:max_count], start=1):
            objs.append(
                HotSpot(
                    place=place,
                    start_date=start,
                    end_date=end,
                    score=score,
                    rank=idx,
                )
            )

        HotSpot.objects.bulk_create(objs)
        self.stdout.write(self.style.SUCCESS(f"🔥 HotSpot {len(objs)}개 생성"))

    # ---------- TrendSpot ----------

    def _create_trendspots(self, start, end, max_count=50):
        """
        나이대별(10S, 20S, ...) TrendSpot 생성
        """

        # (코드, 최소나이, 최대나이)
        age_groups = [
            ("10S", 10, 19),
            ("20S", 20, 29),
            ("30S", 30, 39),
            ("40S", 40, 49),
            ("50S", 50, 59),
            ("60P", 60, 120),
        ]

        # 기준 연도: 집계 기간 끝나는 해
        ref_year = end.year

        for code, min_age, max_age in age_groups:
            users = self._users_in_age_range(ref_year, min_age, max_age)
            if not users.exists():
                continue

            scores = self._calc_place_scores_by_users(users, start, end)
            ranked_places = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            objs = []
            for idx, (place, score) in enumerate(ranked_places[:max_count], start=1):
                objs.append(
                    TrendSpot(
                        place=place,
                        age_group=code,
                        start_date=start,
                        end_date=end,
                        score=score,
                        rank=idx,
                    )
                )

            TrendSpot.objects.bulk_create(objs)
            self.stdout.write(
                self.style.SUCCESS(f"📈 TrendSpot[{code}] {len(objs)}개 생성")
            )

        # 글로벌(전체) 트렌드도 만들고 싶으면 여기서 한 번 더 place_scores 사용해서 생성해도 됨

    def _users_in_age_range(self, ref_year, min_age, max_age):
        """
        ref_year 기준으로 min_age ~ max_age 인 유저 찾기
        age = ref_year - birth_year
        """
        max_birth_year = ref_year - min_age  # 예: 2025 - 20 = 2005
        min_birth_year = ref_year - max_age  # 예: 2025 - 29 = 1996

        return User.objects.filter(
            birth_year__isnull=False,
            birth_year__gte=min_birth_year,
            birth_year__lte=max_birth_year,
        )

    def _calc_place_scores_by_users(self, users, start, end):
        """
        특정 유저 집합(users)에 대해서만 좋아요/위시리스트 기준 점수 계산
        (조회수는 전유저 공통이라 여기선 제외)
        """
        scores = {}
        user_ids = users.values_list("uuid", flat=True)  # User PK 필드명에 맞게 사용

        for place in TravelPlace.objects.all():
            likes = TravelPlaceLike.objects.filter(
                place=place,
                user_id__in=user_ids,
                created_at__range=(start, end),
            ).count()

            wishlist_adds = WishlistItem.objects.filter(
                travel_spot=place,
                wishlist__user_id__in=user_ids,
                created_at__range=(start, end),
            ).count()

            score = likes * 3 + wishlist_adds * 5

            if score > 0:
                scores[place] = score

        return scores
