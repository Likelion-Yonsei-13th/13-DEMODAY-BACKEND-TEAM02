from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, filters
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Request, Root, ThemeTag
from .serializers import RequestSerializer, RootSerializer, ThemeTagSerializer
from .permissions import IsOwnerOrReadOnly, CanCreateRequest, CanCreateRoot


# -------- Request --------
class RequestListCreateView(generics.ListCreateAPIView):
    """
    GET: 누구나(비로그인 포함) 조회 가능
    POST: 로그인 + role == USER만 생성 가능
    """
    queryset = Request.objects.select_related("user", "place").all()
    serializer_class = RequestSerializer
    permission_classes = [CanCreateRequest]  # SAFE_METHODS 허용 + USER만 POST 허용

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["place", "date", "user"]
    # travel_type는 ManyToMany(ThemeTag)이므로 name 기준으로 검색
    search_fields = ["travel_type__name", "experience"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-created_at"]


class RequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: 모두 허용
    PATCH/PUT/DELETE: 소유자 또는 staff만
    """
    queryset = Request.objects.select_related("user", "place").all()
    serializer_class = RequestSerializer
    permission_classes = [IsOwnerOrReadOnly]


# -------- Root --------
class RootListCreateView(generics.ListCreateAPIView):
    """
    GET: 누구나(비로그인 포함) 조회 가능
    POST: 로그인 + role == LOCAL만 생성 가능
    """
    queryset = Root.objects.select_related("founder", "place").all()
    serializer_class = RootSerializer
    permission_classes = [CanCreateRoot]  # SAFE_METHODS 허용 + LOCAL만 POST 허용

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["place", "founder"]
    # Root도 ThemeTag ManyToMany를 사용하므로 name 기준 검색
    search_fields = ["travel_type__name", "experience"]
    ordering_fields = ["created_at", "modified_at"]
    ordering = ["-created_at"]


class RootRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: 모두 허용
    PATCH/PUT/DELETE: 소유자 또는 staff만
    """
    queryset = Root.objects.select_related("founder", "place").all()
    serializer_class = RootSerializer
    permission_classes = [IsOwnerOrReadOnly]


# -------- ThemeTag (읽기 전용) --------
class ThemeTagListView(generics.ListAPIView):
    """
    여행 테마 태그 목록 조회
    - GET: 누구나(비로그인 포함) 조회 가능
    - 필터:
        ?level=1             -> level=1 태그만
        ?parent=<id>         -> 해당 parent를 가진 태그만
        ?level=2&parent=3    -> level=2 & parent=3 인 태그들
    """
    queryset = ThemeTag.objects.select_related("parent").all()
    serializer_class = ThemeTagSerializer
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["level", "parent"]
    ordering_fields = ["level", "id", "name"]
    ordering = ["level", "id"]
