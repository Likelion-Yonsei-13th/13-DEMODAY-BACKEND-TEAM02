from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, filters, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Request, Root, ThemeTag, Rating, RequestRootMap
from .serializers import RequestSerializer, RootSerializer, ThemeTagSerializer, RatingSerializer
from .permissions import IsOwnerOrReadOnly, CanCreateRequest, CanCreateRoot


# -------- Request --------
class RequestListCreateView(generics.ListCreateAPIView):
    """
    GET: 누구나(비로그인 포함) 조회 가능
    POST: 로그인 + role == USER만 생성 가능
    """
    queryset = Request.objects.select_related("user", "place").prefetch_related("proposals__root__founder").all()
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
    queryset = Request.objects.select_related("user", "place").prefetch_related("proposals__root__founder").all()
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
    ordering_fields = ["created_at", "modified_at", "average_rating"]
    ordering = ["-average_rating", "-created_at"]


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


# -------- RequestRootMap (로컬 제안 - 요청서에 대한 대답) --------
class ProposalSendView(generics.CreateAPIView):
    """
    POST: 로컬이 요청서에 대한 대답 제안서 전송
    query_params: request_id (필수)
    """
    serializer_class = RootSerializer
    permission_classes = [IsAuthenticated, CanCreateRoot]
    
    def create(self, request, *args, **kwargs):
        # request_id를 GET 매개변수로 받아서 request 조회
        request_id = request.query_params.get('request_id')
        if not request_id:
            return Response(
                {"error": "request_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_request = Request.objects.get(id=request_id)
        except Request.DoesNotExist:
            return Response(
                {"error": "Request not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Root 생성
        root_data = request.data.copy()
        root_serializer = RootSerializer(data=root_data, context={'request': request})
        if root_serializer.is_valid():
            root = root_serializer.save()
            
            # RequestRootMap 생성 (로컬의 대답으로 기록)
            RequestRootMap.objects.create(
                request=target_request,
                root=root,
                acceptance=False,
                is_finished=False,
                rating=0,
                review=""
            )
            
            return Response(root_serializer.data, status=status.HTTP_201_CREATED)
        return Response(root_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------- ProposalAccept (\uc5ec\ud96c\ub0b4 \uc218\ub77d) --------
class ProposalAcceptView(APIView):
    """
    PATCH: \uc5ec\ud96c\ub0b4\uac00 \ub85c\uceec \uc81c\uc548\uc744 \uc218\ub77d
    query_params: request_id, root_id (\ub450 \uc544\ub9cc\ub4dc)
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        request_id = request.query_params.get('request_id')
        root_id = request.query_params.get('root_id')
        
        if not request_id or not root_id:
            return Response(
                {"error": "request_id and root_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            proposal_map = RequestRootMap.objects.get(
                request_id=request_id,
                root_id=root_id
            )
        except RequestRootMap.DoesNotExist:
            return Response(
                {"error": "Proposal not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # \uc5ec\ud96c\ub0b4\uac00 request\uc758 \uc18c\uc720\uc790\uc778\uc9c0 \ud655\uc778
        if proposal_map.request.user_id != request.user.id:
            return Response(
                {"error": "You can only accept your own proposals"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # \uc218\ub77d \uc2a4\ub2e4\ub08c \uc5c5\ub370\uc774\ud2b8
        proposal_map.acceptance = True
        proposal_map.is_finished = True
        proposal_map.save()
        
        return Response({
            "status": "success",
            "message": "\ub85c\uceec \uc81c\uc548\uc744 \uc218\ub77d\ud588\uc2b5\ub2c8\ub2e4.",
            "acceptance": True,
            "is_finished": True
        }, status=status.HTTP_200_OK)


# -------- Rating (\uc81c\uc548\uc11c \ud3c9\uc810) --------
class RatingListCreateView(generics.ListCreateAPIView):
    queryset = Rating.objects.select_related("root", "user").all()
    serializer_class = RatingSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["root", "user"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        rating = serializer.save()
        root = rating.root
        ratings = list(root.ratings.all())
        root.average_rating = (
            sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        )
        root.rating_count = len(ratings)
        root.save()


class RatingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.select_related("root", "user").all()
    serializer_class = RatingSerializer
    permission_classes = [AllowAny]

    def perform_update(self, serializer):
        rating = serializer.save()
        root = rating.root
        ratings = list(root.ratings.all())
        root.average_rating = (
            sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        )
        root.rating_count = len(ratings)
        root.save()

    def perform_destroy(self, instance):
        root = instance.root
        instance.delete()
        ratings = list(root.ratings.all())
        root.average_rating = (
            sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        )
        root.rating_count = len(ratings)
        root.save()
