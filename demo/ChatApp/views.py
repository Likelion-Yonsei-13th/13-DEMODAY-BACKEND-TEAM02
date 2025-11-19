# ChatApp/views.py
from django.db.models import Q
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer
from .permissions import IsRoomParticipant
from .pagination import MessageCursorPagination


class ChatRoomViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    """
    채팅방 목록/조회/생성
    - 생성(create): payload {"proposal": <RequestRootMap id>}
      → proposal에서 requester/proposer를 자동 세팅
      → 이미 동일 proposal의 방이 있으면 멱등적으로 기존 방 반환(200)
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated, IsRoomParticipant]

    def get_queryset(self):
        u = self.request.user
        return ChatRoom.objects.filter(
            Q(requester_id=u.id) | Q(proposer_id=u.id)
        ).order_by("-last_msg_at", "-created_at")

    def create(self, request, *args, **kwargs):
        proposal_id = request.data.get("proposal")
        if not proposal_id:
            return Response({"detail": "proposal required"}, status=400)

        # proposal에서 requester/proposer 추론
        from DocumentApp.models import RequestRootMap
        try:
            rmap = RequestRootMap.objects.select_related(
                "request__user", "root__founder"
            ).get(pk=proposal_id)
        except RequestRootMap.DoesNotExist:
            return Response({"detail": "proposal not found"}, status=404)

        requester_id = rmap.request.user_id
        proposer_id = rmap.root.founder_id

        # --- ⬇️ 디버깅 코드 추가 ⬇️ ---
        print("--- [ChatRoom Create] 디버깅 ---")
        print(f"로그인 유저 (request.user.id): {request.user.id} (타입: {type(request.user.id)})")
        print(f"추출된 요청자 (requester_id):   {requester_id} (타입: {type(requester_id)})")
        print(f"추출된 제안자 (proposer_id):   {proposer_id} (타입: {type(proposer_id)})")
        print(f"로그인 유저가 참여자인가? {request.user.id in (requester_id, proposer_id)}")
        print("---------------------------------")
        # --- ⬆️ 디버깅 코드 추가 ⬆️ ---

        # 접근 권한: 참여자만 생성 가능
        if request.user.id not in (requester_id, proposer_id):
            return Response(status=403)

        room, created = ChatRoom.objects.get_or_create(
            proposal_id=proposal_id,
            defaults={"requester_id": requester_id, "proposer_id": proposer_id},
        )
        ser = self.get_serializer(room)
        return Response(
            ser.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class ChatMessageViewSet(mixins.ListModelMixin,
                         mixins.CreateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    메시지 목록/생성/소프트삭제
    - 목록(list): /chat/rooms/{room_id}/messages/  (Nested Router)
                  기본 is_deleted=False, 최신순 커서 페이지네이션
    - 생성(create): TEXT or IMAGE 메시지, sender는 요청자 본인으로 강제
    - 삭제(destroy): 보낸 사람만 is_deleted=True로 변경
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated, IsRoomParticipant]
    pagination_class = MessageCursorPagination

    def get_queryset(self):
        room_id = self.kwargs.get("room_pk") or self.request.query_params.get("room")
        return ChatMessage.objects.filter(
            room_id=room_id, is_deleted=False
        ).order_by("-created_at", "-id")

    def create(self, request, *args, **kwargs):
        room_id = self.kwargs.get("room_pk") or request.data.get("room")
        if not room_id:
            return Response({"detail": "room required"}, status=400)

        # 참여자 검증
        try:
            room = ChatRoom.objects.only("id", "requester_id", "proposer_id").get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return Response({"detail": "room not found"}, status=404)
        if request.user.id not in (room.requester_id, room.proposer_id):
            return Response(status=403)

        data = request.data.copy()
        data["room"] = room_id
        data["sender"] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        msg = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(msg).data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.sender_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["GET"], url_path="search")
    def search(self, request, *args, **kwargs):
        """
        내 방들 전체에서 본문 검색
        GET /chat/rooms/{room_id}/messages/search/?q=...  (nested 경로에서도 동작)
        혹은 /chat/rooms/messages/search/?q=... (비중첩 등록 시)
        """
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response({"detail": "q required"}, status=400)

        u = request.user
        rooms = ChatRoom.objects.filter(Q(requester_id=u.id) | Q(proposer_id=u.id))
        qs = ChatMessage.objects.filter(
            room__in=rooms, body__icontains=q, is_deleted=False
        ).order_by("-created_at", "-id")

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page, many=True)
        return self.get_paginated_response(ser.data)
