from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from rest_framework import generics, permissions, status, parsers
from rest_framework.views import APIView
from rest_framework.response import Response

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer
from .permissions import IsChatParticipant


class ChatRoomListCreateView(generics.ListCreateAPIView):
    """
    GET /chat/rooms/      : 내가 참여 중인 방 목록
    POST /chat/rooms/     : { "proposal": <id> } 로 방 생성
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(requester=user) | Q(proposer=user)
        ).order_by("-last_msg_at", "-id")

    def perform_create(self, serializer):
        # serializer.create 에서 참여자/권한 체크
        serializer.save()


class ChatRoomDetailView(generics.RetrieveAPIView):
    """
    GET /chat/rooms/<room_id>/
    """
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated, IsChatParticipant]


class ChatMessageListCreateView(generics.ListCreateAPIView):
    """
    GET  /chat/rooms/<room_id>/messages/
    POST /chat/rooms/<room_id>/messages/
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChatParticipant]

    def get_room(self):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(ChatRoom, pk=room_id)
        # object-level permission 수동 체크
        self.check_object_permissions(self.request, room)
        return room

    def get_queryset(self):
        room = self.get_room()
        return room.messages.filter(is_deleted=False).order_by("id")

    def perform_create(self, serializer):
        room = self.get_room()
        serializer.save(room=room)


class ChatMessageDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /chat/messages/<msg_id>/
    DELETE /chat/messages/<msg_id>/   -> 실제 삭제 대신 soft delete
    """
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChatParticipant]

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


class ChatImageUploadView(APIView):
    """
    POST /chat/rooms/<room_id>/upload-image/

    - multipart/form-data 로 이미지 파일 업로드
      - field name: "image"
      - 선택적으로 "body" 에 캡션 텍스트 포함 가능
    - media/ 아래에 파일 저장 후, IMAGE 타입 ChatMessage 생성
    - 생성된 메시지를 WebSocket 그룹에도 브로드캐스트
    - 응답으로 ChatMessageSerializer 결과 반환
    """
    permission_classes = [permissions.IsAuthenticated, IsChatParticipant]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request, room_id):
        # 1) 방 확인 + 참여자 권한 체크
        room = get_object_or_404(ChatRoom, pk=room_id)
        self.check_object_permissions(request, room)

        # 2) 파일 파라미터 확인
        image_file = request.FILES.get("image")
        if not image_file:
            return Response(
                {"detail": "image 파일이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) 파일 저장 경로 및 저장
        #    예: media/chat/rooms/2/원본파일명
        path = f"chat/rooms/{room_id}/{image_file.name}"
        saved_path = default_storage.save(path, ContentFile(image_file.read()))
        file_url = request.build_absolute_uri(default_storage.url(saved_path))

        # 4) 캡션(body) 옵션 처리
        body = request.data.get("body") or ""

        # 5) IMAGE 타입 ChatMessage 생성
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            msg_type=ChatMessage.Type.IMAGE,
            body=body,
            image_url=file_url,
            image_size_bytes=image_file.size,
        )

        # 6) last_msg 갱신
        room.last_msg = message
        room.last_msg_at = message.created_at
        room.save(update_fields=["last_msg", "last_msg_at"])

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            event_message = {
                "id": message.id,
                "room": message.room_id,
                "sender": message.sender_id,
                "msg_type": message.msg_type,
                "body": message.body,
                "image_url": message.image_url,
                "image_size_bytes": message.image_size_bytes,
                "created_at": message.created_at.isoformat(),
                "is_deleted": message.is_deleted,
            }

            # 🔴 여기! consumer 의 group_name 규칙과 똑같이 맞춰야 함
            group_name = f"chat_{room.id}"

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat.message",  # ChatConsumer.chat_message 로 라우트
                    "message": event_message,
                },
            )

        # 8) HTTP 응답 (업로더 쪽은 이걸 사용해서 UI 갱신해도 됨)
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatRoomFinishView(generics.UpdateAPIView):
    """
    PATCH /chat/rooms/<room_id>/finish/

    - 여행 매칭 확정 → RequestRootMap.is_finished = True
    - WebSocket 참여자들에게도 알림
    """
    queryset = ChatRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsChatParticipant]

    def patch(self, request, *args, **kwargs):
        room = self.get_object()

        # 1) RequestRootMap 가져오기 (여행 요청서)
        request_root = room.proposal   # ChatRoom(proposal FK) 구조 기준

        if not request_root:
            return Response(
                {"detail": "RequestRootMap(proposal) 이 존재하지 않습니다."},
                status=400
            )

        # 2) is_finished 값을 True 로 변경
        request_root.is_finished = True
        request_root.save(update_fields=["is_finished"])

        # 3) WebSocket 참여자들에게 push
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.id}",
            {
                "type": "chat.room_status",
                "message": {
                    "room_id": room.id,
                    "request_root_id": request_root.id,
                    "is_finished": True,
                }
            }
        )

        return Response(
            {
                "detail": "RequestRootMap marked as finished.",
                "room_id": room.id,
                "request_root_id": request_root.id
            },
            status=status.HTTP_200_OK
        )

