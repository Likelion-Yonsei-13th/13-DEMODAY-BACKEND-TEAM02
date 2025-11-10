from django.urls import path
from .views import (
    RequestListCreateView,
    RequestRetrieveUpdateDestroyView,
    RootListCreateView,
    RootRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Requests
    path("requests/", RequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<int:pk>/", RequestRetrieveUpdateDestroyView.as_view(), name="request-detail"),

    # Roots
    path("roots/", RootListCreateView.as_view(), name="root-list-create"),
    path("roots/<int:pk>/", RootRetrieveUpdateDestroyView.as_view(), name="root-detail"),
]
