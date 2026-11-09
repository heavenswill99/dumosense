
from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner

from health_reserve.models import HealthReserveAssessment
from consent.models import Consent, ConsentHistory
from assessments.models import AssessmentType, AssessmentSession
from mindguard.models import CognitiveResult
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)

# # from rest_framework.views import APIView
# # from rest_framework.exceptions import (
# #     PermissionDenied as DRFPermissionDenied,
# #     ValidationError as DRFValidationError,
# )

from intelligence.orchestration import process_mindguard_assessment


class DumosenseTestRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        kwargs["aliases"] = set(kwargs.get("aliases") or ()) | {"default"}
        old_config = super().setup_databases(**kwargs)

        connection = connections["default"]

        database_name = connection.settings_dict["NAME"]
        allowed_name = settings.DATABASES["default"]["TEST"]["NAME"]

        print("Test setup result:", old_config)
        print("Connection NAME:", database_name)
        print("Configured TEST NAME:", allowed_name)

        # SAFETY: Never modify the development database.
        if (
            not database_name.startswith("test_")
            or database_name != allowed_name
        ):
            raise RuntimeError(
                "Unmanaged test tables can only be created "
                "in the configured test database."
            )

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            actual_database = cursor.fetchone()[0]

        print("Actual MySQL database:", actual_database)

        if actual_database != allowed_name:
            raise RuntimeError(
                "MySQL is not connected to the configured test database."
            )

        existing_tables = set(
            connection.introspection.table_names()
        )

        # Preserve the existing test database collation policy.
        with connection.cursor() as cursor:
            quoted_name = connection.ops.quote_name(database_name)
            cursor.execute(
                f"ALTER DATABASE {quoted_name} "
                "CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_0900_ai_ci"
            )


        # Parent tables must exist before dependent tables.
        models = (
            Consent,
            ConsentHistory,
            HealthReserveAssessment,
            AssessmentType,
            AssessmentSession,
            CognitiveResult,
        )

        # The existing users.user_id column uses utf8mb4_unicode_ci.
        # Create new test tables with a matching collation.
        #
        # This applies only to tables created in test_dumosense_dev.
        with connection.cursor() as cursor:
            cursor.execute(
                "SET SESSION collation_connection = 'utf8mb4_unicode_ci'"
            )

        # Use the existing test database collation for compatibility.
        # The database itself is intentionally test-only.
        with connection.cursor() as cursor:
            quoted_name = connection.ops.quote_name(database_name)
            cursor.execute(
                f"ALTER DATABASE {quoted_name} "
                "CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )

        # Refresh the table list because an earlier interrupted
        # setup may have created some tables already.
        existing_tables = set(
            connection.introspection.table_names()
        )

        with connection.schema_editor() as schema_editor:
            for model in models:
                table_name = model._meta.db_table

                if table_name not in existing_tables:
                    print("Creating test table:", table_name)
                    schema_editor.create_model(model)
                    existing_tables.add(table_name)

        return old_config
