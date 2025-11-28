from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.conf import settings
import os


class ImageUploadView(APIView):
    """
    제안서 이미지 업로드 엔드포인트
    POST /document/upload-image/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('image')
        if not file:
            return Response(
                {"error": "이미지 파일이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파일 저장
        filename = default_storage.save(f'root_images/{file.name}', file)
        file_url = default_storage.url(filename)

        # 절대 URL로 변환
        if not file_url.startswith('http'):
            file_url = request.build_absolute_uri(settings.MEDIA_URL + filename)

        return Response({
            "url": file_url,
            "filename": os.path.basename(filename)
        }, status=status.HTTP_201_CREATED)
