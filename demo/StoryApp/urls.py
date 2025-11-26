from django.urls import path
from StoryApp.views import (
    StoryListCreateView,
    StoryDetailView,
    StoryAddViewCountView,
    StoryLikeToggleView,
    CommentListCreateView,
    CommentDeleteView,
)
from StoryApp.upload_views import ImageUploadView

urlpatterns = [
    # 이미지 업로드
    path("upload-image/", ImageUploadView.as_view()),
    # 글
    path("stories/", StoryListCreateView.as_view()),
    path("stories/<int:pk>/", StoryDetailView.as_view()),
    path("stories/<int:story_id>/view/", StoryAddViewCountView.as_view()),
    path("stories/<int:story_id>/like/", StoryLikeToggleView.as_view()),
    # 댓글
    path("stories/<int:story_id>/comments/", CommentListCreateView.as_view()),
    path("comments/<int:pk>/", CommentDeleteView.as_view()),
]
