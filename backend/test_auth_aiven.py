from django.test import override_settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()
client = APIClient()

email = f"dumosense-test-{uuid.uuid4().hex[:10]}@example.com"
password = "DumoTest@2026Secure!"

try:
    with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"]):
        registration = client.post(
            "/api/v1/auth/register/",
            {
                "first_name": "Dumo",
                "last_name": "Test",
                "email": email,
                "password": password,
            },
            format="json",
        )

        print("Registration status:", registration.status_code)
        print("Registration response:", registration.data)

        user = User.objects.filter(email=email).first()

        if user:
            print("User saved in Aiven:", True)
            print("Password verified:", user.check_password(password))
            print("Account status:", user.account_status)

            login = client.post(
                "/api/v1/auth/login/",
                {"email": email, "password": password},
                format="json",
            )

            print("Login status:", login.status_code)
            print("Access token issued:", bool(login.data.get("access")))

            if login.status_code == 200:
                client.credentials(
                    HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
                )

                me = client.get("/api/v1/auth/me/")
                print("Current user status:", me.status_code)
                print("Current user email:", me.data.get("email"))
        else:
            print("Registration did not create a user.")

finally:
    user = User.objects.filter(email=email).first()
    if user:
        user.delete()
        print("Temporary user deleted:", True)
