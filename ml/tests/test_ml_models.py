"""Tests for the standalone synthetic ML benchmark contract."""

import unittest

import numpy as np
import pandas as pd

from modeling.train_ml_models import CLASS_FEATURES, PRIOR_FEATURES, binary_metrics, cohort, regression_metrics, select_threshold


class FeatureContractTests(unittest.TestCase):
    def test_regression_does_not_include_current_result(self):
        self.assertNotIn("accuracy_rate", PRIOR_FEATURES)
        self.assertNotIn("log_rt", PRIOR_FEATURES)
        self.assertIn("accuracy_rate", CLASS_FEATURES)
        self.assertIn("log_rt", CLASS_FEATURES)

    def test_time_and_user_cohorts(self):
        cutoff = pd.Timestamp("2026-05-01T00:00:00Z")
        frame = pd.DataFrame({
            "split": ["train", "train", "development", "development", "test", "test"],
            "index_time": pd.to_datetime(["2026-04-30", "2026-05-01", "2026-04-30",
                                          "2026-05-01", "2026-04-30", "2026-05-01"], utc=True),
        })
        self.assertEqual(cohort(frame, "train", cutoff).index.tolist(), [0])
        self.assertEqual(cohort(frame, "development", cutoff).index.tolist(), [3])
        self.assertEqual(cohort(frame, "test", cutoff).index.tolist(), [5])


class MetricTests(unittest.TestCase):
    def test_confusion_and_probability_metrics(self):
        result = binary_metrics(np.array([1, 1, 0, 0]), np.array([.9, .2, .7, .1]), .5)
        self.assertEqual([result[k] for k in ["TP", "TN", "FP", "FN"]], [1, 1, 1, 1])
        self.assertAlmostEqual(result["balanced_accuracy"], .5)
        self.assertIsNotNone(result["brier"])

    def test_anomaly_scores_are_not_probabilities(self):
        result = binary_metrics(np.array([1, 0]), np.array([5.0, 2.0]), 3.0,
                                probabilities=False)
        self.assertEqual([result["TP"], result["TN"]], [1, 1])
        self.assertIsNone(result["brier"])
        self.assertIsNone(result["log_loss"])
        self.assertEqual(result["roc_auc"], 1.0)

    def test_threshold_selection_uses_development_values(self):
        y = np.array([0, 0, 1, 1])
        p = np.array([.1, .2, .8, .9])
        threshold, sweep = select_threshold(y, p)
        self.assertEqual(len(sweep), 17)
        self.assertEqual(binary_metrics(y, p, threshold)["balanced_accuracy"], 1.0)

    def test_regression_errors(self):
        result = regression_metrics(np.array([1.0, 2.0]), np.array([2.0, 2.0]))
        self.assertEqual(result["n"], 2)
        self.assertAlmostEqual(result["mae"], .5)
        self.assertAlmostEqual(result["rmse"], np.sqrt(.5))


if __name__ == "__main__":
    unittest.main()
