from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated

from .models import UserProfile, ProductEnrollment
from .serializers import UserProfileSerializer, ProductEnrollmentSerializer

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .serializers import UserRegistrationSerializer
from .serializers import CurrentUserSerializer

from django.conf import settings
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            UserProfile.objects.select_related("user"),
            user=self.request.user,
        )


class ProductEnrollmentListView(generics.ListAPIView):
    serializer_class = ProductEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductEnrollment.objects.filter(
            user=self.request.user
        ).order_by("enrolled_at")



class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "Account created successfully.",
                "user": {
                    "user_id": user.user_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = CurrentUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class BrowserLoginJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Login must work without an existing access token.
        return None

@method_decorator(csrf_protect, name="dispatch")
class BrowserLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [BrowserLoginJWTAuthentication]

    def post(self, request):
        serializer = TokenObtainPairSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data
        user = serializer.user

        response = Response({
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "account_status": user.account_status,
        })

        cookie_secure = not settings.DEBUG

        response.set_cookie(
            key="dumosense_access",
            value=tokens["access"],
            httponly=True,
            secure=cookie_secure,
            samesite="Lax",
            max_age=15 * 60,
            path="/api/",
        )

        response.set_cookie(
            key="dumosense_refresh",
            value=tokens["refresh"],
            httponly=True,
            secure=cookie_secure,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
            path="/api/v1/auth/",
        )

        # Make sure the browser has a CSRF token cookie.
       # Generate a CSRF token for the browser.
        get_token(request._request)

        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "message": "CSRF cookie initialized."
        })



@method_decorator(csrf_protect, name="dispatch")
class BrowserRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [BrowserLoginJWTAuthentication]

    def post(self, request):
        # Read the refresh token from the HTTP-only cookie.
        refresh_token = request.COOKIES.get(
            "dumosense_refresh"
        )

        # Reject requests without a refresh token.
        if not refresh_token:
            raise InvalidToken(
                "Refresh token is missing."
            )

        # Validate the token and generate replacement tokens.
        serializer = TokenRefreshSerializer(
            data={"refresh": refresh_token}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            raise InvalidToken(
                "Refresh token is invalid or expired."
            )

        tokens = serializer.validated_data
        cookie_secure = not settings.DEBUG

        response = Response(
            {
                "message": "Session refreshed successfully."
            },
            status=status.HTTP_200_OK
        )

        # Replace the access token cookie.
        response.set_cookie(
            key="dumosense_access",
            value=tokens["access"],
            httponly=True,
            secure=cookie_secure,
            samesite="Lax",
            max_age=15 * 60,
            path="/api/",
        )

        # Replace the refresh cookie when rotation is enabled.
        if "refresh" in tokens:
            response.set_cookie(
                key="dumosense_refresh",
                value=tokens["refresh"],
                httponly=True,
                secure=cookie_secure,
                samesite="Lax",
                max_age=7 * 24 * 60 * 60,
                path="/api/v1/auth/",
            )

        return response


@method_decorator(csrf_protect, name="dispatch")
class BrowserLogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [BrowserLoginJWTAuthentication]

    def post(self, request):
        refresh_token = request.COOKIES.get(
            "dumosense_refresh"
        )

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                # Clear cookies even if the token has expired
                # or has already been blacklisted.
                pass

        response = Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK
        )

        response.delete_cookie(
            key="dumosense_access",
            path="/api/",
            samesite="Lax",
        )

        response.delete_cookie(
            key="dumosense_refresh",
            path="/api/v1/auth/",
            samesite="Lax",
        )

        return response
