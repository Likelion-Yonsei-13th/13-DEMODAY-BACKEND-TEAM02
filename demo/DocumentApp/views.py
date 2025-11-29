# -*- coding: utf-8 -*-
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
    GET: Public
    POST: Authenticated USER role only
    """
    queryset = Request.objects.select_related("user", "place").prefetch_related("proposals__root__founder").all()
    serializer_class = RequestSerializer
    permission_classes = [CanCreateRequest]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["place", "date", "user"]
    search_fields = ["travel_type__name", "experience"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-created_at"]


class RequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Public
    PATCH/PUT/DELETE: Owner only
    """
    queryset = Request.objects.select_related("user", "place").prefetch_related("proposals__root__founder").all()
    serializer_class = RequestSerializer
    permission_classes = [IsOwnerOrReadOnly]


# -------- Root --------
class RootListCreateView(generics.ListCreateAPIView):
    """
    GET: Public
    POST: Authenticated LOCAL role only
    """
    queryset = Root.objects.select_related("founder", "place").all()
    serializer_class = RootSerializer
    permission_classes = [CanCreateRoot]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["place", "founder"]
    search_fields = ["travel_type__name", "experience"]
    ordering_fields = ["created_at", "modified_at", "average_rating"]
    ordering = ["-average_rating", "-created_at"]


class RootRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Public
    PATCH/PUT/DELETE: Owner only
    """
    queryset = Root.objects.select_related("founder", "place").all()
    serializer_class = RootSerializer
    permission_classes = [IsOwnerOrReadOnly]


# -------- ThemeTag --------
class ThemeTagListView(generics.ListAPIView):
    """
    Travel theme tag list
    - GET: Public access
    - Filters:
        ?level=1             -> Only level=1 tags
        ?parent=<id>         -> Tags with specific parent
        ?level=2&parent=3    -> level=2 & parent=3 tags
    """
    queryset = ThemeTag.objects.select_related("parent").all()
    serializer_class = ThemeTagSerializer
    permission_classes = [AllowAny]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["level", "parent"]
    ordering_fields = ["level", "id", "name"]
    ordering = ["level", "id"]


# -------- RequestRootMap --------
class ProposalSendView(generics.CreateAPIView):
    """
    POST: Create proposal by local in response to traveler request
    query_params: request_id (required)
    """
    serializer_class = RootSerializer
    permission_classes = [IsAuthenticated, CanCreateRoot]
    
    def create(self, request, *args, **kwargs):
        # Get request_id from query parameters
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
        
        # Create Root object
        root_data = request.data.copy()
        root_serializer = RootSerializer(data=root_data, context={'request': request})
        if root_serializer.is_valid():
            root = root_serializer.save()
            
            # Create RequestRootMap
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


# -------- ProposalAccept --------
class ProposalAcceptView(APIView):
    """
    PATCH: Accept proposal by traveler
    query_params: request_id, root_id (both required)
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
        
        # Verify ownership - only the traveler (request owner) can accept
        if str(proposal_map.request.user_id) != str(request.user.id):
            return Response(
                {"error": f"Only the traveler can accept proposals. Expected user {proposal_map.request.user_id}, got {request.user.id}"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update acceptance status
        proposal_map.acceptance = True
        proposal_map.is_finished = True
        proposal_map.save()
        
        return Response({
            "status": "success",
            "message": "Proposal accepted successfully",
            "acceptance": True,
            "is_finished": True
        }, status=status.HTTP_200_OK)


# -------- Rating --------
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
