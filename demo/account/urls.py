from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    LogoutView,
    MeView,
    # onboarding
    OnboardingNextView,
    InterestListView,
    InstagramRequestView,
    InstagramConfirmView,
    InstagramStatusView,
    LocalProfileView,
    UserProfileView,
    SwitchRoleView,
)

urlpatterns = [
    # auth
    path("signup/", RegisterView.as_view(), name="signup"),
    path("verify-email/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    # onboarding flow
    path("onboarding/next/", OnboardingNextView.as_view()),
    path("interests/", InterestListView.as_view()),
    path("profile/local/", LocalProfileView.as_view()),
    path("profile/user/", UserProfileView.as_view()),
    path("role/switch/", SwitchRoleView.as_view()),
    path("instagram/request/", InstagramRequestView.as_view()),
    path("instagram/confirm/", InstagramConfirmView.as_view()),
    path("instagram/status/", InstagramStatusView.as_view()),
]
