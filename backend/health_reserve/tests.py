from decimal import Decimal

from django.test import SimpleTestCase

from .calculations import calculate_preparedness


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