from django.urls import path
from .views import (
    RequestListCreateView,
    RequestRetrieveUpdateDestroyView,
    RootListCreateView,
    RootRetrieveUpdateDestroyView,
    ThemeTagListView,
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
]
