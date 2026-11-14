"""Assert the test runner rejects unsafe configuration before database setup."""
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from config.mindguard_test_runner import IsolatedMindGuardRunner


class MindGuardIsolationTests(SimpleTestCase):
    def test_unsafe_database_settings_are_rejected_before_setup(self):
        safe = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "TEST": {"NAME": ":memory:"}}
        for changes in ({"ENGINE": "django.db.backends.mysql", "NAME": "defaultdb"},
                        {"NAME": "defaultdb"}, {"NAME": "test.sqlite3"},
                        {"HOST": "operational.example.invalid"}, {"USER": "operational"},
                        {"TEST": {"NAME": "defaultdb"}}):
            with self.subTest(changes=changes), patch("config.mindguard_test_runner.connections",
                    {"default": SimpleNamespace(settings_dict={**safe, **changes})}), patch(
                    "django.test.runner.DiscoverRunner.setup_databases") as setup:
                with self.assertRaises(RuntimeError):
                    IsolatedMindGuardRunner().setup_databases()
                setup.assert_not_called()

    @override_settings(MINDGUARD_ISOLATED_TESTS=False)
    def test_missing_explicit_isolation_flag_is_rejected(self):
        with patch("django.test.runner.DiscoverRunner.setup_databases") as setup:
            with self.assertRaises(RuntimeError):
                IsolatedMindGuardRunner().setup_databases()
        setup.assert_not_called()

    def test_additional_database_alias_is_rejected(self):
        with patch("config.mindguard_test_runner.connections", {"default": None, "other": None}), patch(
                "django.test.runner.DiscoverRunner.setup_databases") as setup:
            with self.assertRaises(RuntimeError):
                IsolatedMindGuardRunner().setup_databases()
        setup.assert_not_called()
