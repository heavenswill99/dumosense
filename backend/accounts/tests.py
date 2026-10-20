
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404, response
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .views import UserProfileView, ProductEnrollmentListView


from django.urls import reverse
from rest_framework.test import APIClient

from .models import User

from django.test import override_settings


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


class UserDatabaseIntegrationTests(TestCase):

    def test_user_table_is_available(self):
        from .models import User

        self.assertEqual(User.objects.count(), 0)


class UserLoginTests(TestCase):

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

class UserRegistrationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user_register")

        self.valid_data = {
            "first_name": "Ada",
            "last_name": "Okafor",
            "email": "ada@example.com",
            "password": "StrongPassword123!"
        }

    def test_registration_creates_user(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        user = User.objects.get(
            email="ada@example.com"
        )

        self.assertEqual(user.first_name, "Ada")
        self.assertTrue(
            user.check_password("StrongPassword123!")
        )

        self.assertNotEqual(
            user.password,
            "StrongPassword123!"
        )

    def test_duplicate_email_is_rejected(self):
        self.client.post(
            self.url,
            self.valid_data,
            format="json"
        )

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            User.objects.filter(
                email="ada@example.com"
            ).count(),
            1
        )

    def test_password_is_not_returned(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json"
        )

        self.assertNotIn(
            "password",
            str(response.data)
        )


class CurrentUserTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("current_user")

        self.user = User.objects.create_user(
            user_id="USRTEST0001",
            first_name="Ada",
            last_name="Okafor",
            email="ada@example.com",
            password="StrongPassword123!"
        )

    def test_authenticated_user_can_view_account(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["email"],
            "ada@example.com"
        )
        self.assertEqual(
            response.data["user_id"],
            self.user.user_id
        )

    def test_unauthenticated_user_cannot_view_account(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_password_is_not_returned(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertNotIn("password", response.data)



class JWTLoginTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            user_id="USRLOGIN001",
            first_name="Ada",
            last_name="Okafor",
            email="ada@example.com",
            password="StrongPassword123!"
        )

        self.login_url = reverse("token_obtain_pair")
        self.me_url = reverse("current_user")

    def test_valid_login_returns_tokens(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "ada@example.com",
                "password": "StrongPassword123!"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "ada@example.com",
                "password": "WrongPassword123!"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 401)

    def test_access_token_can_retrieve_current_user(self):
        login_response = self.client.post(
            self.login_url,
            {
                "email": "ada@example.com",
                "password": "StrongPassword123!"
            },
            format="json"
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["user_id"],
            self.user.user_id
        )



class BrowserAuthenticationTests(TestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

        self.user = User.objects.create_user(
            user_id="USRBROWSER001",
            first_name="Ada",
            last_name="Okafor",
            email="browser@example.com",
            password="StrongPassword123!"
        )

        self.csrf_url = reverse("csrf_token")
        self.login_url = reverse("browser_login")
        self.me_url = reverse("current_user")

        self.credentials = {
            "email": "browser@example.com",
            "password": "StrongPassword123!"
        }

    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_login_without_csrf_is_rejected(self):
        response = self.client.post(
            self.login_url,
            self.credentials,
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_valid_browser_login_sets_cookies(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("dumosense_access", response.cookies)
        self.assertIn("dumosense_refresh", response.cookies)

        self.assertTrue(
            response.cookies["dumosense_access"]["httponly"]
        )
        self.assertTrue(
            response.cookies["dumosense_refresh"]["httponly"]
        )

    def test_invalid_password_is_rejected(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            self.login_url,
            {
                "email": "browser@example.com",
                "password": "WrongPassword123!"
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )


        self.assertEqual(response.status_code, 401)

    def test_cookie_can_access_current_user(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["user_id"],
            self.user.user_id
        )


    def test_browser_refresh_success(self):
        # Initialize CSRF protection.
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        # Log in to obtain authentication cookies.
        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        old_access = self.client.cookies["dumosense_access"].value

        # Request a refreshed session.
        response = self.client.post(
            reverse("browser_refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("dumosense_access", response.cookies)
        self.assertIn("dumosense_refresh", response.cookies)
        self.assertTrue(response.cookies["dumosense_access"]["httponly"])

        # The refreshed access token should remain valid.
        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(
            me_response.data["user_id"],
            self.user.user_id
        )

    def test_browser_refresh_without_token(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            reverse("browser_refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 401)

    def test_browser_refresh_with_invalid_token(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        self.client.cookies["dumosense_refresh"] = "invalid-token"

        response = self.client.post(
            reverse("browser_refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 401)

    def test_browser_refresh_without_csrf(self):
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        # No CSRF header is supplied for this request.
        response = self.client.post(
            reverse("browser_refresh"),
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 403)


    def test_browser_logout_clears_cookies(self):
        # Initialize CSRF and log in.
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        # Log out.
        response = self.client.post(
            reverse("browser_logout"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)

        # Confirm authentication cookies were cleared.
        self.assertIn("dumosense_access", response.cookies)
        self.assertIn("dumosense_refresh", response.cookies)

        self.assertEqual(
            response.cookies["dumosense_access"].value,
            ""
        )
        self.assertEqual(
            response.cookies["dumosense_refresh"].value,
            ""
        )

        # The browser should no longer be authenticated.
        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, 401)

    def test_browser_logout_without_csrf_is_rejected(self):
        # Log in with valid CSRF.
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        # Attempt logout without CSRF header.
        response = self.client.post(
            reverse("browser_logout"),
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_browser_logout_blacklists_refresh_token(self):
        # Initialize CSRF and log in.
        self.client.get(self.csrf_url)
        csrf_token = self.client.cookies["csrftoken"].value

        login_response = self.client.post(
            self.login_url,
            self.credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, 200)

        # Save the original refresh token for reuse testing.
        old_refresh = self.client.cookies[
            "dumosense_refresh"
        ].value

        # Log out.
        logout_response = self.client.post(
            reverse("browser_logout"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(logout_response.status_code, 200)

        # Try to reuse the blacklisted refresh token.
        self.client.cookies["dumosense_refresh"] = old_refresh

        refresh_response = self.client.post(
            reverse("browser_refresh"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(refresh_response.status_code, 401)
