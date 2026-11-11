from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

User = get_user_model()

test_user = User(user_id="TEST_CONSENT_001")

client = APIClient()
client.force_authenticate(user=test_user)

paths = [
    "/api/v1/mindguard/results/",
    "/api/v1/mindguard/wellbeing/history/",
    "/api/v1/mindguard/context/history/",
]

with override_settings(
    ALLOWED_HOSTS=[*settings.ALLOWED_HOSTS, "testserver"]
):
    with patch(
        "consent.permissions.Consent.objects.filter"
    ) as mock_filter:

        mock_filter.return_value.exists.return_value = True

        for path in paths:
            response = client.get(path)

            print(f"{path} -> HTTP {response.status_code}")
            print("Response:", response.data)