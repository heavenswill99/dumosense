"""Tests for the cost-free Health Reserve buffer rank."""

import csv
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest

from health_reserve.score import SCORE_LOWER_BOUNDS, score_assessment, score_buffer, summarize_csv
from health_reserve.statistical_baseline import build_records, run


class BufferScoreTests(unittest.TestCase):
    def test_exact_thresholds_and_range(self):
        for expected, lower in enumerate(SCORE_LOWER_BOUNDS, start=1):
            self.assertEqual(score_buffer(lower * 100, 100)["score"], expected)
        self.assertEqual(score_buffer(0, 100)["score"], 1)
        self.assertEqual(score_buffer(100000, 100)["score"], 10)

    def test_monotonic_and_scale_invariant(self):
        self.assertLessEqual(score_buffer(300, 100)["score"], score_buffer(400, 100)["score"])
        self.assertGreaterEqual(score_buffer(300, 100)["score"], score_buffer(300, 200)["score"])
        self.assertEqual(score_buffer(300, 100)["score"], score_buffer(300000, 100000)["score"])

    def test_invalid_inputs_fail_closed(self):
        for amount, obligations in ((-1, 100), (100, 0), (float("nan"), 100),
                                    ("", 100), (100, float("inf")), (True, 100),
                                    (1e308, 1e-308)):
            with self.subTest(amount=amount, obligations=obligations):
                with self.assertRaises(ValueError):
                    score_buffer(amount, obligations)

    def test_cost_derived_fields_and_coverage_do_not_change_score(self):
        base = {"current_preparedness_amount": 300, "monthly_financial_obligations": 100,
                "emergency_health_resources": 100, "healthcare_coverage_status": "partial"}
        changed = {**base, "estimated_healthcare_exposure": 999999,
                   "preparedness_target": 1, "preparedness_gap": 999,
                   "preparedness_ratio": 2.4, "reserve_status": "strong",
                   "healthcare_coverage_status": "uninsured",
                   "emergency_health_resources": 0, "number_of_dependants": 5}
        self.assertEqual(score_assessment(base)["score"], score_assessment(changed)["score"])
        self.assertNotEqual(score_assessment(base)["health_resource_obligation_months"],
                            score_assessment(changed)["health_resource_obligation_months"])

    def test_latest_snapshot_uses_assessment_time_not_file_order(self):
        fields = ["reserve_assessment_id", "user_id", "assessed_at",
                  "current_preparedness_amount", "monthly_financial_obligations"]
        rows = [
            ["B", "U1", "2026-02-01T00:00:00", 1200, 100],
            ["C", "U2", "2026-01-01T00:00:00", 50, 100],
            ["A", "U1", "2026-01-01T00:00:00", 0, 100],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assessments.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                writer.writerows(rows)
            report = summarize_csv(path)
        self.assertEqual(report["rows"], 3)
        self.assertEqual(report["users_with_valid_assessment"], 2)
        self.assertEqual(report["latest_user_score_counts"]["10"], 1)
        self.assertEqual(report["latest_user_score_counts"]["3"], 1)


class StatisticalBaselineTests(unittest.TestCase):
    def test_strictly_prior_median_and_same_timestamp_ties(self):
        def item(name, date, months):
            row = {"reserve_assessment_id": name, "user_id": "U1",
                   "assessed_at": date, "current_preparedness_amount": months * 100,
                   "monthly_financial_obligations": 100}
            return ("U1", datetime.fromisoformat(date), name, row)
        rows = [
            item("E", "2026-05-01T00:00:00", 6),
            item("C", "2026-03-01T00:00:00", 2),
            item("A", "2026-01-01T00:00:00", 0),
            item("D1", "2026-04-01T00:00:00", 3),
            item("D2", "2026-04-01T00:00:00", 4),
            item("B", "2026-02-01T00:00:00", 1),
        ]
        result = {row["reserve_assessment_id"]: row for row in build_records(rows)}
        for name in ("A", "B", "C"):
            self.assertFalse(result[name]["baseline_available"])
        for name in ("D1", "D2"):
            self.assertEqual(result[name]["prior_assessment_count"], 3)
            self.assertEqual(result[name]["prior_median_buffer_months"], 1)
        self.assertEqual(result["E"]["prior_assessment_count"], 5)
        self.assertEqual(result["E"]["prior_median_buffer_months"], 2)
        self.assertEqual(result["E"]["delta_from_prior_median_months"], 4)

    def test_old_history_is_not_a_current_baseline(self):
        def item(name, date):
            row = {"reserve_assessment_id": name, "user_id": "U1",
                   "assessed_at": date, "current_preparedness_amount": 100,
                   "monthly_financial_obligations": 100}
            return ("U1", datetime.fromisoformat(date), name, row)
        records = build_records([item("A", "2024-01-01"), item("B", "2024-02-01"),
                                 item("C", "2024-03-01"), item("D", "2026-01-01")])
        latest = next(row for row in records if row["reserve_assessment_id"] == "D")
        self.assertEqual(latest["prior_assessment_count"], 0)
        self.assertIsNone(latest["prior_median_buffer_months"])

    def test_failed_run_preserves_latest_success(self):
        fields = ["reserve_assessment_id", "user_id", "assessed_at",
                  "current_preparedness_amount", "monthly_financial_obligations"]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "input.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                writer.writerow(["A", "U1", "2026-01-01", 100, 100])
            output = base / "runs"
            completed = run(source, output)
            pointer = json.loads((output / "latest_successful_health_reserve_run.json").read_text())
            self.assertEqual(pointer["run_id"], completed.name)
            with source.open("a", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(["A", "U1", "2026-02-01", 100, 100])
            with self.assertRaises(ValueError):
                run(source, output)
            pointer_after = json.loads((output / "latest_successful_health_reserve_run.json").read_text())
            self.assertEqual(pointer, pointer_after)


if __name__ == "__main__":
    unittest.main()
