from datetime import datetime, timedelta, timezone
from unittest import TestCase

from mindguard.reflection_stats import summarize_ratings


class ReflectionStatisticsTests(TestCase):
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)

    def record(self, days_ago, **ratings):
        return (
            self.now - timedelta(days=days_ago),
            [{"question": question, "value": value} for question, value in ratings.items()],
        )

    def test_uses_five_most_recent_prior_ratings(self):
        ratings = [5, 1, 2, 3, 4, 5, 1]
        records = [self.record(day, sleep=value) for day, value in enumerate(ratings)]
        item, = summarize_ratings(["sleep"], records)
        self.assertEqual(item["latest_rating"], 5)
        self.assertEqual(item["prior_count"], 5)
        self.assertEqual(item["prior_median"], 3)
        self.assertEqual(item["difference_from_prior_median"], 2)
        self.assertEqual(item["status"], "comparison_available")

    def test_skips_unanswered_items_and_does_not_combine_questions(self):
        records = [
            self.record(0, sleep=5),
            self.record(1, mood=2),
            self.record(2, sleep=1),
            self.record(3, sleep=2),
            self.record(4, sleep=3),
        ]
        sleep, mood, stress = summarize_ratings(["sleep", "mood", "stress"], records)
        self.assertEqual(sleep["prior_median"], 2)
        self.assertEqual(mood["latest_recorded_at"], self.now - timedelta(days=1))
        self.assertEqual(mood["status"], "insufficient_history")
        self.assertIsNone(mood["prior_median"])
        self.assertEqual(stress["status"], "missing_rating")
        self.assertIsNone(stress["latest_rating"])

    def test_excludes_tied_timestamps_and_invalid_ratings(self):
        records = [
            self.record(0, focus=5),
            self.record(0, focus=1),
            self.record(1, focus=True),
            self.record(2, focus=7),
            self.record(3, focus=3),
            self.record(3, focus=4),
            self.record(4, focus=2),
        ]
        item, = summarize_ratings(["focus"], records)
        self.assertEqual(item["latest_rating"], 5)
        self.assertEqual(item["prior_count"], 2)
        self.assertIsNone(item["prior_median"])
        self.assertEqual(item["status"], "insufficient_history")
