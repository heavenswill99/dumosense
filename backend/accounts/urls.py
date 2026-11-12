from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import BrowserLogoutView, CSRFTokenView, UserProfileView, UserRegistrationView, CurrentUserView, BrowserLoginView, BrowserRefreshView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("register/", UserRegistrationView.as_view(), name="user_register"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("browser-login/", BrowserLoginView.as_view(), name="browser_login"),
    path("csrf/",CSRFTokenView.as_view(),name="csrf_token"),
    path("browser-refresh/",BrowserRefreshView.as_view(),name="browser_refresh"),
    path("browser-logout/",BrowserLogoutView.as_view(),name="browser_logout"),
]
