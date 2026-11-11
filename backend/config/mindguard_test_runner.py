"""Fail-closed isolation and test-only provisioning for unmanaged MindGuard tables."""
from django.conf import settings
from django.db import connections
from django.test import TestCase
from django.test.runner import DiscoverRunner


def assert_isolated_configuration(*, before_setup=False):
    if (not getattr(settings, "MINDGUARD_ISOLATED_TESTS", False)
            or settings.TEST_RUNNER != "config.mindguard_test_runner.IsolatedMindGuardRunner"
            or set(connections) != {"default"} or settings.DATABASE_ROUTERS):
        raise RuntimeError("MindGuard database tests require the dedicated isolated settings.")
    configuration = connections["default"].settings_dict
    name = configuration["NAME"]
    in_memory = name == ":memory:" or (
        not before_setup and isinstance(name, str) and name.startswith("file:memorydb_")
        and "mode=memory" in name
    )
    if (configuration["ENGINE"] != "django.db.backends.sqlite3" or not in_memory
            or configuration["TEST"]["NAME"] != ":memory:"
            or any(configuration.get(key) for key in ("HOST", "USER", "PASSWORD", "PORT"))):
        raise RuntimeError("Refusing MindGuard database setup outside SQLite in memory.")


class IsolatedMindGuardRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # Check before DiscoverRunner can create, migrate, or destroy anything.
        assert_isolated_configuration(before_setup=True)
        old_config = super().setup_databases(**kwargs)
        assert_isolated_configuration()
        from consent.models import Consent, ConsentHistory
        from assessments.models import AssessmentType, CognitiveTask, AssessmentSession
        from mindguard.models import CognitiveResponse, CognitiveResult, WellbeingCheckin, ContextRecord
        from intelligence.models import IntelligenceRun, Insight, Recommendation, Action

        connection = connections["default"]
        existing = set(connection.introspection.table_names())
        with connection.schema_editor() as editor:
            for model in (Consent, ConsentHistory, AssessmentType, CognitiveTask, AssessmentSession,
                          CognitiveResponse, CognitiveResult, WellbeingCheckin, ContextRecord,
                          IntelligenceRun, Insight, Recommendation, Action):
                if model._meta.db_table not in existing:
                    editor.create_model(model)
                    existing.add(model._meta.db_table)
        return old_config


class MindGuardDatabaseTestCase(TestCase):
    """Extra per-class guard; no hardcoded MySQL SELECT DATABASE() calls."""
    @classmethod
    def setUpClass(cls):
        assert_isolated_configuration()
        super().setUpClass()
