"""Contract tests for the Health Reserve next-assessment ML benchmark."""

import unittest

import numpy as np

from health_reserve.predict_ml_models import prepare
from health_reserve.train_ml_models import (
    FAMILIES, FEATURES, band_index, classification_metrics, configurations,
    regression_metrics, user_split,
)


class HealthReserveMLTests(unittest.TestCase):
    def test_four_supervised_families_plus_anomaly_comparator(self):
        self.assertEqual(FAMILIES, ("linear", "random_forest", "catboost", "lightgbm"))
        for family in FAMILIES:
            self.assertEqual(len(configurations(family, "classification")), 2)
            self.assertEqual(len(configurations(family, "regression")), 2)

    def test_score_bands(self):
        self.assertEqual([band_index(i) for i in range(1, 11)],
                         [0, 0, 0, 1, 1, 1, 2, 2, 3, 3])

    def test_features_exclude_future_and_cost_generated_labels(self):
        forbidden = {"next_score", "next_band", "next_at", "horizon_days", "user_id",
                     "estimated_healthcare_exposure", "preparedness_target",
                     "preparedness_gap", "preparedness_ratio", "reserve_status"}
        self.assertFalse(forbidden.intersection(FEATURES))
        self.assertIn("score", FEATURES)

    def test_user_split_is_deterministic(self):
        self.assertEqual(user_split("USR000001"), user_split("USR000001"))
        self.assertIn(user_split("USR000001"), ("train", "development", "test"))

    def test_inference_requires_point_in_time_history(self):
        assessment = {
            "current_preparedness_amount": 300000,
            "monthly_financial_obligations": 100000,
            "emergency_health_resources": 50000,
            "healthcare_coverage_status": "partial",
            "number_of_dependants": 2,
            "prior_assessment_count": 0,
            "prior_median_buffer_months": None,
            "delta_from_prior_median_months": None,
            "latest_prior_age_days": None,
        }
        frame = prepare(assessment, list(FEATURES))
        self.assertEqual(frame.loc[0, "score"], 6)
        self.assertEqual(frame.loc[0, "health_resource_obligation_months"], 0.5)
        with self.assertRaises(ValueError):
            prepare({k: v for k, v in assessment.items() if k != "prior_assessment_count"}, list(FEATURES))
        inconsistent = {**assessment, "prior_assessment_count": 3,
                        "prior_median_buffer_months": 1.0,
                        "delta_from_prior_median_months": 999.0,
                        "latest_prior_age_days": 40.0}
        with self.assertRaises(ValueError):
            prepare(inconsistent, list(FEATURES))

    def test_metric_arithmetic(self):
        labels = np.array([0, 1, 2, 3])
        probability = np.eye(4) * 0.96 + 0.01
        classification = classification_metrics(labels, labels, probability)
        self.assertEqual(classification["accuracy"], 1.0)
        self.assertEqual(classification["balanced_accuracy"], 1.0)
        self.assertEqual(classification["macro_f1"], 1.0)
        self.assertEqual(classification["confusion_matrix"], np.eye(4, dtype=int).tolist())
        self.assertIsNone(classification_metrics(labels, labels, None)["log_loss"])
        regression = regression_metrics(np.array([1, 3, 5, 10]),
                                        np.array([1.5, 3.5, 4.5, 9.5]))
        self.assertAlmostEqual(regression["mae_score_points"], 0.5)
        self.assertAlmostEqual(regression["rmse_score_points"], 0.5)
        self.assertEqual(regression["rounded_within_one_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
