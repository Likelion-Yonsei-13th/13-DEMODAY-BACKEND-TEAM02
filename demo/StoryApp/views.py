from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Q, F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from StoryApp.models import TravelStory, StoryLike, StoryComment
from StoryApp.serializers import (
    StoryCreateSerializer,
    StoryListSerializer,
    StoryDetailSerializer,
    CommentSerializer,
)


# --------------------------
# 권한
# --------------------------
class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return (
            getattr(obj, "author_id", None) == getattr(request.user, "id", None)
            or request.user.is_staff
        )


# --------------------------
# 글 목록/작성
# --------------------------
class StoryListCreateView(generics.ListCreateAPIView):
    """
    GET /story/stories/?sort=latest|hot_week|hot_month
                       &country=KR&state=서울특별시&city=마포구&district=서교동
                       &q=검색어
    POST /story/stories/
    {
      "country":"KR","state":"서울특별시","city":"마포구","district":"서교동",
      "place": 1,                # 선택
      "title":"밤의 홍대 산책",
      "content":"분위기 최고...",
      "photo_url":"https://...",
      "is_public":true
    }
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = TravelStory.objects.filter(is_public=True).select_related(
        "place", "author"
    )
    serializer_class = StoryListSerializer

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoryCreateSerializer
        return StoryListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params

        # 지역 필터
        for key in ("country", "state", "city", "district"):
            val = p.get(key)
            if val:
                qs = qs.filter(**{key: val})

        # 검색
        q = p.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))

        # 정렬
        sort = (p.get("sort") or "latest").lower()
        now = timezone.now()

        if sort == "hot_week":
            start = now - timedelta(days=7)
            qs = qs.annotate(
                likes_recent=Count("likes", filter=Q(likes__created_at__gte=start))
            ).order_by("-likes_recent", "-liked_count", "-view_count", "-id")
        elif sort == "hot_month":
            start = now.replace(day=1)
            qs = qs.annotate(
                likes_recent=Count("likes", filter=Q(likes__created_at__gte=start))
            ).order_by("-likes_recent", "-liked_count", "-view_count", "-id")
        else:
            qs = qs.order_by("-created_at", "-id")

        return qs

    def perform_create(self, serializer):
        serializer.save()  # author는 serializer.create에서 request.user로 세팅됨


# --------------------------
# 글 상세/수정/삭제
# --------------------------
class StoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /story/stories/<id>/
    PATCH /story/stories/<id>/
    DELETE /story/stories/<id>/
    """

    permission_classes = [IsAuthorOrReadOnly]
    queryset = TravelStory.objects.filter(is_public=True).select_related(
        "place", "author"
    )
    
    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return StoryCreateSerializer
        return StoryDetailSerializer


# --------------------------
# 조회수 +1 (선택 호출)
# --------------------------
class StoryAddViewCountView(APIView):
    """
    POST /story/stories/<id>/view/
    """

    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, story_id):
        story = get_object_or_404(TravelStory, pk=story_id, is_public=True)
        TravelStory.objects.filter(pk=story.id).update(view_count=F("view_count") + 1)
        story.refresh_from_db(fields=["view_count"])
        return Response({"view_count": story.view_count})


# --------------------------
# 좋아요 토글
# --------------------------
class StoryLikeToggleView(APIView):
    """
    POST /story/stories/<id>/like/
    -> { "liked": true|false, "liked_count": N }
    """

    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, story_id):
        story = get_object_or_404(TravelStory, pk=story_id, is_public=True)
        user = request.user

        like = StoryLike.objects.filter(story=story, user=user).first()
        if like:
            like.delete()
            TravelStory.objects.filter(pk=story.id).update(
                liked_count=F("liked_count") - 1
            )
            liked = False
        else:
            StoryLike.objects.create(story=story, user=user)
            TravelStory.objects.filter(pk=story.id).update(
                liked_count=F("liked_count") + 1
            )
            liked = True

        story.refresh_from_db(fields=["liked_count"])
        return Response({"liked": liked, "liked_count": story.liked_count})


# --------------------------
# 댓글
# --------------------------
class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET  /story/stories/<id>/comments/
    POST /story/stories/<id>/comments/   { "content": "댓글 내용" }
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = CommentSerializer

    def get_queryset(self):
        story_id = self.kwargs["story_id"]
        return (
            StoryComment.objects.filter(story_id=story_id)
            .select_related("user")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        story_id = self.kwargs["story_id"]
        serializer.save(user=self.request.user, story_id=story_id)


class CommentDeleteView(generics.DestroyAPIView):
    """
    DELETE /story/comments/<id>/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    queryset = StoryComment.objects.all()

    def perform_destroy(self, instance):
        # 작성자나 스태프만 삭제
        if (
            instance.user_id != getattr(self.request.user, "id", None)
            and not self.request.user.is_staff
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("삭제 권한이 없습니다.")
        return super().perform_destroy(instance)
