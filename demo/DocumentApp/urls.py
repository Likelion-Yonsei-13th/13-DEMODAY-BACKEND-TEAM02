from django.urls import path
from .views import (
    RequestListCreateView,
    RequestRetrieveUpdateDestroyView,
    RootListCreateView,
    RootRetrieveUpdateDestroyView,
    ThemeTagListView,
    RatingListCreateView,
    RatingRetrieveUpdateDestroyView,
)
from .upload_views import ImageUploadView

urlpatterns = [
    # Requests
    path("requests/", RequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<int:pk>/", RequestRetrieveUpdateDestroyView.as_view(), name="request-detail"),

    # Roots
    path("roots/", RootListCreateView.as_view(), name="root-list-create"),
    path("roots/<int:pk>/", RootRetrieveUpdateDestroyView.as_view(), name="root-detail"),

    # Theme Tags (읽기 전용 리스트)
    path("theme-tags/", ThemeTagListView.as_view(), name="theme-tag-list"),

    # Image Upload
    path("upload-image/", ImageUploadView.as_view(), name="root-image-upload"),

    # Ratings
    path("ratings/", RatingListCreateView.as_view(), name="rating-list-create"),
    path("ratings/<int:pk>/", RatingRetrieveUpdateDestroyView.as_view(), name="rating-detail"),
]
