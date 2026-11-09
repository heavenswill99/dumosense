import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from health_reserve.extended_models import FinancialProfiles

settings.ALLOWED_HOSTS = [
    *settings.ALLOWED_HOSTS,
    "testserver",
]

User = get_user_model()

url = "/api/v1/health-reserve/financial-profile/"

profiles = list(
    FinancialProfiles.objects.select_related("user")
    .order_by("financial_profile_id")[:2]
)

if not profiles:
    print("No financial profiles found.")
    raise SystemExit(0)

user_a = profiles[0].user

# Find a second user with a financial profile
profile_b = (
    FinancialProfiles.objects
    .exclude(user_id=user_a.pk)
    .select_related("user")
    .first()
)

user_b = profile_b.user if profile_b else None


def get_records(response):
    data = response.json()

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        results = data.get("results")

        if isinstance(results, list):
            return results

    raise ValueError("Unexpected API response structure")


def check_ownership(records, user):
    if not records:
        return False

    return all(
        FinancialProfiles.objects.filter(
            financial_profile_id=item["financial_profile_id"],
            user=user,
        ).exists()
        for item in records
    )


print("\n=== TEST 1: ANONYMOUS ACCESS ===")

anonymous_client = APIClient()
response = anonymous_client.get(url)

print("Status:", response.status_code)
print("Passed:", response.status_code in [401, 403])


print("\n=== TEST 2: USER A ACCESS ===")

client_a = APIClient()
client_a.force_authenticate(user=user_a)

response_a = client_a.get(url)

print("Status:", response_a.status_code)

if response_a.status_code == 200:
    records_a = get_records(response_a)

    print("Returned records:", len(records_a))
    print(
        "Ownership verified:",
        check_ownership(records_a, user_a)
    )


print("\n=== TEST 3: CROSS-USER ISOLATION ===")

if user_b is None:
    print(
        "SKIPPED: A second user with a "
        "financial profile is required."
    )
else:
    response_b = client_a.get(url)

    if response_b.status_code == 200:
        records = get_records(response_b)

        user_b_records_exposed = any(
            FinancialProfiles.objects.filter(
                financial_profile_id=item["financial_profile_id"],
                user=user_b,
            ).exists()
            for item in records
        )

        print(
            "User B records exposed to User A:",
            user_b_records_exposed
        )

        print(
            "Isolation passed:",
            not user_b_records_exposed
        )
    else:
        print("Status:", response_b.status_code)


print("\n=== TEST 4: USER B ACCESS ===")

if user_b is None:
    print("SKIPPED: No second profile owner found.")
else:
    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    response_b = client_b.get(url)

    print("Status:", response_b.status_code)

    if response_b.status_code == 200:
        records_b = get_records(response_b)

        print("Returned records:", len(records_b))
        print(
            "Ownership verified:",
            check_ownership(records_b, user_b)
        )


print("\n=== FINANCIAL PROFILE READ TESTS COMPLETE ===")