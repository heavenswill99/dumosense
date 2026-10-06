import unittest
from dumosense_ai.service import compose_insight


class DumosenseAITest(unittest.TestCase):
    def mg(self):
        return {"user_id": "u1", "run_id": "run1", "model_version": "MG1",
                "session_id": "s1", "index_time": "2026-01-10T12:00:00+00:00",
                "current_performance": {"accuracy": 0.8},
                "baselines": {"per_domain": {"n_valid": 3, "median": 0.7,
                                              "ts_max_prior": "2026-01-09T12:00:00+00:00"}}}

    def hr(self):
        return {"user_id": "u1", "model_version": "HR1",
                "reserve_assessment_id": "h1", "assessed_at": "2026-01-10T12:00:00",
                "score": 6, "obligation_buffer_months": 3.0,
                "prior_assessment_count": 3, "prior_median_buffer_months": 2.0,
                "delta_from_prior_median_months": 1.0}

    def call(self, record=None, product="MINDGUARD", **kwargs):
        source = {"status": "completed", "run_id": "run1", "model_version": "MG1" if product == "MINDGUARD" else "HR1", "product_code": product}
        inputs = dict(product_code=product, authenticated_user_id="u1",
                      consent_verified=True, enrollment_verified=True, source_run=source)
        inputs.update(kwargs)
        return compose_insight(record if record is not None else self.mg(), **inputs)

    def test_mindguard_comparison_and_deterministic_id(self):
        a = self.call()
        self.assertEqual(a, self.call())
        self.assertEqual(a["product_code"], "MINDGUARD")
        self.assertIn("80.0%", a["insight"]["insight_text"])
        self.assertLessEqual(len(a["insight"]["insight_id"]), 20)
        self.assertFalse(a["delivery"]["automatic_alert"])

    def test_health_reserve_keeps_separate_product_and_score(self):
        a = self.call(self.hr(), "HEALTH_RESERVE")
        self.assertEqual(a["insight"]["insight_type"], "buffer_comparison")
        self.assertIn("3.0 months", a["insight"]["insight_text"])
        self.assertNotEqual(a["insight"]["insight_id"], self.call()["insight"]["insight_id"])

    def test_identity_consent_enrollment(self):
        for change in ({"authenticated_user_id": "other"}, {"consent_verified": False},
                       {"enrollment_verified": False}):
            with self.subTest(change=change), self.assertRaises(PermissionError):
                self.call(**change)

    def test_rejects_wrong_run_or_product(self):
        with self.assertRaises(ValueError):
            self.call(source_run={"status": "completed", "run_id": "other",
                                  "model_version": "MG1", "product_code": "MINDGUARD"})
        with self.assertRaises(ValueError):
            self.call(self.hr(), "MINDGUARD")
        with self.assertRaises(ValueError):
            self.call(source_run={"status": "failed", "run_id": "run1",
                                  "model_version": "MG1", "product_code": "MINDGUARD"})

    def test_rejects_future_mindguard_history(self):
        record = self.mg()
        record["baselines"]["per_domain"]["ts_max_prior"] = record["index_time"]
        with self.assertRaises(ValueError):
            self.call(record)

    def test_rejects_inconsistent_reserve_rank_or_baseline(self):
        record = self.hr()
        record["score"] = 10
        with self.assertRaises(ValueError):
            self.call(record, "HEALTH_RESERVE")
        record = self.hr()
        record["delta_from_prior_median_months"] = 9
        with self.assertRaises(ValueError):
            self.call(record, "HEALTH_RESERVE")


if __name__ == "__main__":
    unittest.main()
