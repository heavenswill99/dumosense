from decimal import Decimal
from urllib import response

from django.test import SimpleTestCase

from .calculations import calculate_preparedness
from .progress import calculate_progress
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from consent.models import Consent
from .models import HealthReserveAssessment



class HealthReserveCalculationTests(SimpleTestCase):

    def test_preparedness_gap_and_ratio(self):
        result = calculate_preparedness(
            preparedness_target=500000,
            available_amount=150000,
        )

        self.assertEqual(
            result["preparedness_gap"],
            Decimal("350000.00"),
        )

        self.assertEqual(
            result["preparedness_ratio"],
            Decimal("0.300000"),
        )

    def test_target_fully_met(self):
        result = calculate_preparedness(
            preparedness_target=500000,
            available_amount=500000,
        )

        self.assertEqual(
            result["preparedness_gap"],
            Decimal("0.00"),
        )

        self.assertEqual(
            result["preparedness_ratio"],
            Decimal("1.000000"),
        )

    def test_amount_above_target(self):
        result = calculate_preparedness(
            preparedness_target=500000,
            available_amount=600000,
        )

        self.assertEqual(
            result["preparedness_gap"],
            Decimal("0.00"),
        )

        self.assertEqual(
            result["preparedness_ratio"],
            Decimal("1.200000"),
        )

    def test_zero_target_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_preparedness(
                preparedness_target=0,
                available_amount=150000,
            )

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_preparedness(
                preparedness_target=500000,
                available_amount=-100,
            )

from .serializers import HealthReserveAssessmentCreateSerializer


class HealthReserveSerializerTests(SimpleTestCase):

    def setUp(self):
        self.data = {
            "target_mode": "manual",
            "healthcare_coverage_status": "insured",
            "estimated_healthcare_exposure": "500000.00",
            "emergency_health_resources": "50000.00",
            "monthly_financial_obligations": "80000.00",
            "number_of_dependants": 2,
            "current_preparedness_amount": "150000.00",
            "preparedness_target": "500000.00",
        }

    def test_valid_manual_target(self):
        serializer = HealthReserveAssessmentCreateSerializer(
            data=self.data
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_manual_target_is_required(self):
        self.data.pop("preparedness_target")

        serializer = HealthReserveAssessmentCreateSerializer(
            data=self.data
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("preparedness_target", serializer.errors)

    def test_recommended_target_not_yet_available(self):
        self.data["target_mode"] = "recommended"
        self.data.pop("preparedness_target")

        serializer = HealthReserveAssessmentCreateSerializer(
            data=self.data
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("target_mode", serializer.errors)

    def test_negative_preparedness_amount_rejected(self):
        self.data["current_preparedness_amount"] = "-100.00"

        serializer = HealthReserveAssessmentCreateSerializer(
            data=self.data
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "current_preparedness_amount",
            serializer.errors,
        )

from rest_framework.test import APIClient


class HealthReserveAuthenticationTests(SimpleTestCase):

    def test_assessment_history_requires_login(self):
        client = APIClient()

        response = client.get(
            "/api/v1/health-reserve/assessments/"
        )

        self.assertIn(response.status_code, [401, 403])

    def test_progress_requires_login(self):
        client = APIClient()

        response = client.get(
            "/api/v1/health-reserve/progress/"
        )

        self.assertIn(response.status_code, [401, 403])

    def test_assessment_creation_requires_login(self):
        client = APIClient()

        response = client.post(
            "/api/v1/health-reserve/assessments/create/",
            {},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])


class HealthReserveProgressCalculationTests(SimpleTestCase):

    def test_progress_increases(self):
        result = calculate_progress(
            first_amount=100000,
            latest_amount=180000,
            first_target=500000,
            latest_target=600000,
        )

        self.assertEqual(result["amount_change"], 80000)
        self.assertEqual(result["target_change"], 100000)

    def test_progress_decreases(self):
        result = calculate_progress(
            first_amount=180000,
            latest_amount=100000,
            first_target=600000,
            latest_target=500000,
        )

        self.assertEqual(result["amount_change"], -80000)
        self.assertEqual(result["target_change"], -100000)

    def test_no_progress_change(self):
        result = calculate_progress(
            first_amount=100000,
            latest_amount=100000,
            first_target=500000,
            latest_target=500000,
        )

        self.assertEqual(result["amount_change"], 0)
        self.assertEqual(result["target_change"], 0)

class HealthReserveDatabaseIntegrationTests(TestCase):

    def test_assessment_creation_requires_consent(self):
        user = User.objects.create(
            user_id="USR_TEST_HR001",
            first_name="Test",
            last_name="User",
            email="hrtest@example.com",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/v1/health-reserve/assessments/create/",
            {
                "target_mode": "manual",
                "healthcare_coverage_status": "uninsured",
                "estimated_healthcare_exposure": "300000.00",
                "emergency_health_resources": "50000.00",
                "monthly_financial_obligations": "100000.00",
                "number_of_dependants": 2,
                "current_preparedness_amount": "50000.00",
                "preparedness_target": "500000.00",
            },
            format="json",
            HTTP_HOST="testserver",
        )

        print("Response status:", response.status_code)
        print("Response body:", response.content.decode("utf-8")[:1000])
        self.assertEqual(response.status_code, 403)

    def test_assessment_creation_with_granted_consent(self):
        user = User.objects.create(
            user_id="USR_TEST_HR002",
            first_name="Test",
            last_name="Member",
            email="hrmember@example.com",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        Consent.objects.create(
            consent_id="CON_TEST_HR002",
            user=user,
            consent_type="health_reserve_data",
            purpose="Health Reserve assessment",
            consent_version=Decimal("1.00"),
            status="granted",
            granted_at=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/v1/health-reserve/assessments/create/",
            {
                "target_mode": "manual",
                "healthcare_coverage_status": "uninsured",
                "estimated_healthcare_exposure": "300000.00",
                "emergency_health_resources": "50000.00",
                "monthly_financial_obligations": "100000.00",
                "number_of_dependants": 2,
                "current_preparedness_amount": "50000.00",
                "preparedness_target": "500000.00",
            },
            format="json",
            HTTP_HOST="testserver",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            HealthReserveAssessment.objects.filter(user=user).count(),
            1,
        )
        self.assertEqual(
            Decimal(str(response.data["preparedness_gap"])),
            Decimal("450000.00"),
        )

    def test_users_cannot_see_other_users_assessments(self):
        user_a = User.objects.create(
            user_id="USR_TEST_HR003",
            first_name="User",
            last_name="A",
            email="usera@example.com",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        user_b = User.objects.create(
            user_id="USR_TEST_HR004",
            first_name="User",
            last_name="B",
            email="userb@example.com",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        HealthReserveAssessment.objects.create(
            reserve_assessment_id="HRA_TEST_003",
            user=user_a,
            assessed_at=timezone.now(),
            healthcare_coverage_status="uninsured",
            estimated_healthcare_exposure=Decimal("300000.00"),
            emergency_health_resources=Decimal("50000.00"),
            monthly_financial_obligations=Decimal("100000.00"),
            number_of_dependants=2,
            current_preparedness_amount=Decimal("50000.00"),
            preparedness_target=Decimal("500000.00"),
            preparedness_gap=Decimal("450000.00"),
            preparedness_ratio=Decimal("0.100000"),
            reserve_status="below_target",
        )

        client = APIClient()
        client.force_authenticate(user=user_b)

        response = client.get(
            "/api/v1/health-reserve/assessments/",
            HTTP_HOST="testserver",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_health_reserve_progress_tracking(self):
        user = User.objects.create(
            user_id="USR_TEST_HR005",
            first_name="Progress",
            last_name="User",
            email="progress@example.com",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        first_date = timezone.now() - timezone.timedelta(days=30)
        latest_date = timezone.now()

        HealthReserveAssessment.objects.create(
            reserve_assessment_id="HRA_TEST_005A",
            user=user,
            assessed_at=first_date,
            healthcare_coverage_status="uninsured",
            estimated_healthcare_exposure=Decimal("300000.00"),
            emergency_health_resources=Decimal("50000.00"),
            monthly_financial_obligations=Decimal("100000.00"),
            number_of_dependants=2,
            current_preparedness_amount=Decimal("50000.00"),
            preparedness_target=Decimal("500000.00"),
            preparedness_gap=Decimal("450000.00"),
            preparedness_ratio=Decimal("0.100000"),
            reserve_status="below_target",
        )

        HealthReserveAssessment.objects.create(
            reserve_assessment_id="HRA_TEST_005B",
            user=user,
            assessed_at=latest_date,
            healthcare_coverage_status="uninsured",
            estimated_healthcare_exposure=Decimal("300000.00"),
            emergency_health_resources=Decimal("50000.00"),
            monthly_financial_obligations=Decimal("100000.00"),
            number_of_dependants=2,
            current_preparedness_amount=Decimal("150000.00"),
            preparedness_target=Decimal("500000.00"),
            preparedness_gap=Decimal("350000.00"),
            preparedness_ratio=Decimal("0.300000"),
            reserve_status="below_target",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(
            "/api/v1/health-reserve/progress/",
            HTTP_HOST="testserver",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["assessment_count"], 2)

        self.assertEqual(
            Decimal(str(response.data["amount_change"])),
            Decimal("100000.00"),
        )

        self.assertEqual(
            Decimal(str(response.data["target_change"])),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(str(response.data["current_gap"])),
            Decimal("350000.00"),
        )

        self.assertEqual(
            Decimal(str(response.data["current_ratio"])),
            Decimal("0.300000"),
        )