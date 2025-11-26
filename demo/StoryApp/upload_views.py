from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.files.storage import default_storage
from django.conf import settings
import os
import uuid


class ImageUploadView(APIView):
    """
    이미지 업로드 전용 엔드포인트
    POST /story/upload-image/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if 'image' not in request.FILES:
            return Response(
                {"error": "이미지 파일이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']
        
        # 파일 확장자 검증
        ext = os.path.splitext(image_file.name)[1].lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        if ext not in allowed_extensions:
            return Response(
                {"error": f"지원하지 않는 파일 형식입니다. {', '.join(allowed_extensions)}만 가능합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 파일 크기 검증 (10MB)
        if image_file.size > 10 * 1024 * 1024:
            return Response(
                {"error": "파일 크기는 10MB 이하여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 고유 파일명 생성
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join('story_images', unique_filename)
        
        # 파일 저장
        saved_path = default_storage.save(file_path, image_file)
        
        # URL 생성
        file_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)
        
        return Response({
            "url": file_url,
            "filename": unique_filename
        }, status=status.HTTP_201_CREATED)
