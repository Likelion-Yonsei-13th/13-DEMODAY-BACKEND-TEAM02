from django.urls import path
from StoryApp.views import (
    StoryListCreateView,
    StoryDetailView,
    StoryAddViewCountView,
    StoryLikeToggleView,
    CommentListCreateView,
    CommentDeleteView,
)

urlpatterns = [
    # 글
    path("stories/", StoryListCreateView.as_view()),
    path("stories/<int:pk>/", StoryDetailView.as_view()),
    path("stories/<int:story_id>/view/", StoryAddViewCountView.as_view()),
    path("stories/<int:story_id>/like/", StoryLikeToggleView.as_view()),
    # 댓글
    path("stories/<int:story_id>/comments/", CommentListCreateView.as_view()),
    path("comments/<int:pk>/", CommentDeleteView.as_view()),
]
