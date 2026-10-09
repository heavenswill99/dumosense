from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .views import UserProfileView
from .views import ProductEnrollmentListView
from django.test import TestCase


class UserProfileSecurityTests(SimpleTestCase):

    def test_profile_requires_authentication(self):
        request = APIRequestFactory().get("/api/v1/profile/")

        response = UserProfileView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_missing_profile_returns_404(self):
        request = APIRequestFactory().get("/api/v1/profile/")

        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            user_id="USR_TEST001",
        )

        force_authenticate(request, user=user)

        with patch(
            "accounts.views.get_object_or_404",
            side_effect=Http404,
        ):
            response = UserProfileView.as_view()(request)

        self.assertEqual(response.status_code, 404)

    def test_product_enrollments_require_authentication(self):
        request = APIRequestFactory().get("/api/v1/products/")

        response = ProductEnrollmentListView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_product_enrollments_are_filtered_by_user(self):
        request = APIRequestFactory().get("/api/v1/products/")

        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            user_id="USR_TEST001",
        )

        force_authenticate(request, user=user)

        with patch(
            "accounts.views.ProductEnrollment.objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value = []

            response = ProductEnrollmentListView.as_view()(request)

        mock_filter.assert_called_once_with(user=user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_login_rejects_invalid_credentials(self):
        from rest_framework_simplejwt.views import TokenObtainPairView

        request = APIRequestFactory().post(
            "/api/v1/auth/login/",
            {
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        response = TokenObtainPairView.as_view()(request)

        self.assertEqual(response.status_code, 401)

class UserDatabaseIntegrationTests(TestCase):

    def test_user_table_is_available(self):
        from .models import User

        self.assertEqual(User.objects.count(), 0)