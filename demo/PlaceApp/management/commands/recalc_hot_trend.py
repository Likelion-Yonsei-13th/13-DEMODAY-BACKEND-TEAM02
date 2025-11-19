# PlaceApp/management/commands/recalc_hot_trend.py
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

# 모델은 기존 네 구조(원상복구) 가정
from PlaceApp.models import (
    TravelPlace,
    HotSpot,
    TrendSpot,
    TravelPlaceLike,
    WishlistItem,
)

# ---------------------------
# 가중치 / 하이퍼파라미터 (필요하면 커맨드라인 인자로 override)
# ---------------------------
DEFAULT_W_LIKE = 5.0  # 장소 좋아요(기간 내)
DEFAULT_W_WISHLIST = 3.0  # 위시리스트 추가(기간 내)
DEFAULT_W_STORY_POST = 4.0  # 스토리 글 1건(지역→장소 분배)
DEFAULT_W_STORY_LIKE = 2.0  # 스토리 좋아요 1건(지역→장소 분배)

# 장소 분배 기본 가중치: w_i = 1 + likes_count + α*view_count + β*wishlist_total
DEFAULT_ALPHA = 0.0005  # view_count 스케일링
DEFAULT_BETA = 0.5  # (전체 기간) wishlist 누적 스케일링

AGE_GROUP_LABELS = ("10S", "20S", "30S", "40S", "50S", "60S", "70S", "80S", "GLOBAL")


def _tz_aware_start_end(start_str: str, end_str: str):
    """
    YYYY-MM-DD 두 날짜를 [start, end) 구간의 'aware datetime'으로 변환
    (zoneinfo 환경: localize 대신 make_aware 사용)
    """
    tz = timezone.get_current_timezone()  # settings.TIME_ZONE 기반
    start_naive = datetime.strptime(start_str, "%Y-%m-%d")  # 00:00
    end_naive = datetime.strptime(end_str, "%Y-%m-%d") + timedelta(
        days=1
    )  # 다음날 00:00 (exclusive)

    if getattr(settings, "USE_TZ", True):
        start_dt = timezone.make_aware(start_naive, tz)
        end_dt = timezone.make_aware(end_naive, tz)
    else:
        # USE_TZ = False 인 경우 그냥 naive datetime 사용
        start_dt, end_dt = start_naive, end_naive

    return start_dt, end_dt


def _safe_get_age_group(user) -> Optional[str]:
    """
    유저에서 나이대 문자열을 추출. 필드 불명확하므로 여러 패턴 시도.
    없으면 None 반환.
    """
    # 1) 직접 age_group 같은 필드가 있을 때
    for attr in ("age_group", "AGE_GROUP", "ageGroup"):
        if hasattr(user, attr):
            val = getattr(user, attr)
            if isinstance(val, str) and val.strip():
                return val.strip().upper()

    # 2) profile.age_group 같은 형태
    profile = getattr(user, "profile", None)
    if profile is not None:
        for attr in ("age_group", "AGE_GROUP", "ageGroup"):
            if hasattr(profile, attr):
                val = getattr(profile, attr)
                if isinstance(val, str) and val.strip():
                    return val.strip().upper()

    # 3) 생년으로 추정 (YYYY or date)
    for attr in ("birth_year", "BIRTH_YEAR", "birth", "date_of_birth", "dob"):
        if hasattr(user, attr):
            val = getattr(user, attr)
            try:
                # birth_year = int
                year = None
                if isinstance(val, int):
                    year = val
                elif isinstance(val, str) and val.isdigit():
                    year = int(val)
                elif hasattr(val, "year"):
                    year = int(val.year)

                if year and 1900 < year < 2100:
                    from datetime import date

                    age = date.today().year - year
                    decade = max(10, min(80, (age // 10) * 10))
                    return f"{decade}S"
            except Exception:
                pass

    return None


def _total_wishlist_per_place() -> Dict[int, int]:
    """
    전체 기간 위시리스트 누적(분배 가중치용)
    """
    q = (
        WishlistItem.objects.filter(travel_spot__isnull=False)
        .values("travel_spot_id")
        .annotate(c=Count("id"))
    )
    return {row["travel_spot_id"]: row["c"] for row in q}


def _base_weight_for_place(
    p: TravelPlace, total_wishlist_dict: Dict[int, int], alpha: float, beta: float
) -> float:
    wish_tot = total_wishlist_dict.get(p.id, 0)
    return (
        1.0
        + float(p.likes_count)
        + alpha * float(p.view_count)
        + beta * float(wish_tot)
    )


def _region_tuple_of_place(p: TravelPlace) -> Tuple[str, str, str, str]:
    return (p.country or "", p.state or "", p.city or "", p.district or "")


def _iter_story_events(start_dt, end_dt):
    """
    StoryApp(있으면)에서 스토리/스토리좋아요 이벤트를 지역 단위로 집계해서 yield.
    없으면 빈 제너레이터.
    반환 예: ('POST', (country,state,city,district), count, {'age_group': '20S' or None})
            ('LIKE', (....), count, {'age_group': '30S' or None})
    """
    try:
        Story = apps.get_model("StoryApp", "Story")
    except LookupError:
        Story = None

    try:
        StoryLike = apps.get_model("StoryApp", "StoryLike")
    except LookupError:
        StoryLike = None

    if Story:
        # 스토리 글 수(작성자 연령대 기준으로 나눠 계산 가능)
        qs = (
            Story.objects.filter(
                created_at__gte=start_dt, created_at__lt=end_dt, is_public=True
            )
            .select_related("author")
            .only("country", "state", "city", "district", "author_id")
        )
        # 지역별 + 연령대별로 직접 파이썬 집계 (DB 필드 불확실성 때문에)
        bucket = defaultdict(int)
        for s in qs:
            ag = _safe_get_age_group(getattr(s, "author", None))
            key = (
                (s.country or ""),
                (s.state or ""),
                (s.city or ""),
                (s.district or ""),
                ag or "",
            )
            bucket[key] += 1

        for (co, st, ci, di, ag), c in bucket.items():
            yield ("POST", (co, st, ci, di), c, {"age_group": ag or None})

    if StoryLike:
        qs = (
            StoryLike.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
            .select_related("user", "story")
            .only("user_id", "story_id")
        )
        bucket = defaultdict(int)
        for sl in qs:
            story = getattr(sl, "story", None)
            if not story:
                continue
            ag = _safe_get_age_group(getattr(sl, "user", None))
            key = (
                (story.country or ""),
                (story.state or ""),
                (story.city or ""),
                (story.district or ""),
                ag or "",
            )
            bucket[key] += 1

        for (co, st, ci, di, ag), c in bucket.items():
            yield ("LIKE", (co, st, ci, di), c, {"age_group": ag or None})


class Command(BaseCommand):
    """
    방법 B 구현:
    - 기간 내 장소 좋아요/위시리스트 추가 → place 점수 가산
    - 기간 내 스토리/스토리 좋아요(지역 이벤트) → 같은 지역의 place들에 가중치 분배 후 가산
    - HotSpot: place별 총점으로 rank 저장
    - TrendSpot: 연령대별로 동일 계산 (연령 불명은 스킵)
    """

    help = (
        "Recalculate HotSpot & TrendSpot for a period. (Method B + Wishlist included)"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
        parser.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
        parser.add_argument("--dry-run", action="store_true")

        parser.add_argument("--w-like", type=float, default=DEFAULT_W_LIKE)
        parser.add_argument("--w-wishlist", type=float, default=DEFAULT_W_WISHLIST)
        parser.add_argument("--w-story-post", type=float, default=DEFAULT_W_STORY_POST)
        parser.add_argument("--w-story-like", type=float, default=DEFAULT_W_STORY_LIKE)

        parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
        parser.add_argument("--beta", type=float, default=DEFAULT_BETA)

    def handle(self, *args, **opts):
        start_dt, end_dt = _tz_aware_start_end(opts["start"], opts["end"])
        dry_run = bool(opts["dry_run"])

        W_LIKE = float(opts["w_like"])
        W_WISHLIST = float(opts["w_wishlist"])
        W_STORY_POST = float(opts["w_story_post"])
        W_STORY_LIKE = float(opts["w_story_like"])
        ALPHA = float(opts["alpha"])
        BETA = float(opts["beta"])

        self.stdout.write(
            self.style.HTTP_INFO(
                f"[recalc] window=[{start_dt} ~ {end_dt}) dry_run={dry_run} "
                f"W(like)={W_LIKE} W(wishlist)={W_WISHLIST} W(story_post)={W_STORY_POST} W(story_like)={W_STORY_LIKE} "
                f"alpha={ALPHA} beta={BETA}"
            )
        )

        # -------------------------
        # 0) 곳(place) 캐시, 분배용 전체 위시리스트 누적
        # -------------------------
        place_qs = TravelPlace.objects.all().only(
            "id", "likes_count", "view_count", "country", "state", "city", "district"
        )
        place_map: Dict[int, TravelPlace] = {p.id: p for p in place_qs}
        total_wish_map = _total_wishlist_per_place()

        # -------------------------
        # 1) 기간 내 장소 좋아요/위시리스트
        # -------------------------
        like_counts = defaultdict(int)  # place_id -> count
        for row in (
            TravelPlaceLike.objects.filter(
                created_at__gte=start_dt, created_at__lt=end_dt
            )
            .values("place_id")
            .annotate(c=Count("id"))
        ):
            like_counts[row["place_id"]] = row["c"]

        wish_counts = defaultdict(int)  # place_id -> count
        for row in (
            WishlistItem.objects.filter(
                created_at__gte=start_dt,
                created_at__lt=end_dt,
                travel_spot__isnull=False,
            )
            .values("travel_spot_id")
            .annotate(c=Count("id"))
        ):
            wish_counts[row["travel_spot_id"]] = row["c"]

        # -------------------------
        # 2) 스토리(있으면) 지역→장소 분배 (글/좋아요 따로)
        # -------------------------
        distributed_from_story = defaultdict(float)  # place_id -> credit
        distributed_from_story_by_age = defaultdict(
            float
        )  # (age_group, place_id) -> credit

        # region -> place ids 캐시 (자주 쓰이므로)
        def _places_in_region(region: Tuple[str, str, str, str]):
            co, st, ci, di = region
            return [
                p
                for p in place_qs
                if (p.country or "") == co
                and (p.state or "") == st
                and (p.city or "") == ci
                and (p.district or "") == di
            ]

        for kind, region, cnt, meta in _iter_story_events(start_dt, end_dt):
            if cnt <= 0:
                continue
            places = _places_in_region(region)
            if not places:
                continue

            # 분배 가중치 계산
            weights = []
            for p in places:
                w = _base_weight_for_place(p, total_wish_map, ALPHA, BETA)
                weights.append(max(0.000001, w))
            sum_w = sum(weights)
            unit = (W_STORY_POST if kind == "POST" else W_STORY_LIKE) * float(cnt)

            for p, w in zip(places, weights):
                credit = unit * (w / sum_w)
                distributed_from_story[p.id] += credit
                ag = (meta or {}).get("age_group")
                if ag and isinstance(ag, str) and ag.strip():
                    distributed_from_story_by_age[(ag.strip().upper(), p.id)] += credit

        # -------------------------
        # 3) HotSpot 점수 합산 (place별)
        # -------------------------
        score_by_place = defaultdict(float)
        for pid, c in like_counts.items():
            score_by_place[pid] += W_LIKE * float(c)
        for pid, c in wish_counts.items():
            score_by_place[pid] += W_WISHLIST * float(c)
        for pid, v in distributed_from_story.items():
            score_by_place[pid] += float(v)

        # -------------------------
        # 4) TrendSpot (연령대별) 점수
        #    - 장소 좋아요: liker 연령대 기준
        #    - 위시리스트: 생성자(=wishlist.user) 연령대 기준
        #    - 스토리: 위에서 분배된 by_age 그대로 사용
        # -------------------------
        score_by_age_place = defaultdict(float)  # (age_group, place_id) -> score

        # 4-1) 장소 좋아요 by age
        like_qs = (
            TravelPlaceLike.objects.filter(
                created_at__gte=start_dt, created_at__lt=end_dt
            )
            .select_related("user")
            .only("place_id", "user_id")
        )
        for lk in like_qs:
            ag = _safe_get_age_group(getattr(lk, "user", None))
            if not ag:
                continue
            score_by_age_place[(ag, lk.place_id)] += W_LIKE

        # 4-2) 위시리스트 by age
        wish_qs = (
            WishlistItem.objects.filter(
                created_at__gte=start_dt,
                created_at__lt=end_dt,
                travel_spot__isnull=False,
            )
            .select_related("wishlist__user", "travel_spot")
            .only("wishlist_id", "travel_spot_id")
        )
        for wi in wish_qs:
            wl = getattr(wi, "wishlist", None)
            if wl is None:
                continue
            ag = _safe_get_age_group(getattr(wl, "user", None))
            if not ag:
                continue
            score_by_age_place[(ag, wi.travel_spot_id)] += W_WISHLIST

        # 4-3) 스토리 분배분 by age (이미 계산됨)
        for (ag, pid), credit in distributed_from_story_by_age.items():
            score_by_age_place[(ag, pid)] += float(credit)

        # -------------------------
        # 5) DB 반영 (해당 기간만 삭제 후 재생성)
        # -------------------------
        if dry_run:
            self.stdout.write(
                self.style.WARNING("[dry-run] HotSpot/TrendSpot DB write SKIPPED")
            )
            # 출력 요약
            top_hot = sorted(score_by_place.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
            self.stdout.write(self.style.HTTP_INFO("Top10 HotSpot (place_id, score):"))
            for pid, sc in top_hot:
                nm = place_map.get(pid).name if pid in place_map else "?"
                self.stdout.write(f"  #{pid} ({nm}): {sc:.3f}")

            ag_groups = {}
            for (ag, pid), sc in score_by_age_place.items():
                ag_groups.setdefault(ag, 0)
                ag_groups[ag] += sc
            self.stdout.write(
                self.style.HTTP_INFO(f"Trend groups present: {list(ag_groups.keys())}")
            )
            return

        with transaction.atomic():
            HotSpot.objects.filter(
                start_date=start_dt.date(), end_date=(end_dt - timedelta(days=1)).date()
            ).delete()
            TrendSpot.objects.filter(
                start_date=start_dt.date(), end_date=(end_dt - timedelta(days=1)).date()
            ).delete()

            # HotSpot insert
            hot_rows = []
            ranked = sorted(score_by_place.items(), key=lambda x: x[1], reverse=True)
            rank = 1
            for pid, sc in ranked:
                if pid not in place_map:
                    continue
                if sc <= 0:
                    continue
                hot_rows.append(
                    HotSpot(
                        place_id=pid,
                        start_date=start_dt.date(),
                        end_date=(end_dt - timedelta(days=1)).date(),
                        score=float(sc),
                        rank=rank,
                    )
                )
                rank += 1
            HotSpot.objects.bulk_create(hot_rows, batch_size=500)

            # TrendSpot insert (age group별 랭킹)
            trend_rows = []
            # age_group -> [(place_id, score)]
            per_ag: Dict[str, list] = defaultdict(list)
            for (ag, pid), sc in score_by_age_place.items():
                if pid in place_map and sc > 0:
                    per_ag[ag].append((pid, sc))

            for ag, arr in per_ag.items():
                arr.sort(key=lambda x: x[1], reverse=True)
                for idx, (pid, sc) in enumerate(arr, start=1):
                    trend_rows.append(
                        TrendSpot(
                            place_id=pid,
                            age_group=ag,
                            start_date=start_dt.date(),
                            end_date=(end_dt - timedelta(days=1)).date(),
                            score=float(sc),
                            rank=idx,
                        )
                    )
            TrendSpot.objects.bulk_create(trend_rows, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"[done] HotSpot inserted={len(hot_rows)} TrendSpot inserted={len(trend_rows)}"
            )
        )
