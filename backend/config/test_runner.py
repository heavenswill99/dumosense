from django.db import connections
from django.test.runner import DiscoverRunner

from health_reserve.models import HealthReserveAssessment
from consent.models import Consent, ConsentHistory


class DumosenseTestRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)

        connection = connections["default"]

        # Safety: never create these tables outside a test database.
        if connection.settings_dict["NAME"] != "test_dumosense_dev":
            raise RuntimeError(
                "Unmanaged test tables can only be created "
                "in test_dumosense_dev."
            )

        existing_tables = set(
            connection.introspection.table_names()
        )

        # Normalize the test database's character collation.
# This prevents foreign key mismatches between unmanaged tables.
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER DATABASE `test_dumosense_dev` "
                "CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )

        with connection.schema_editor() as schema_editor:
            for model in (
                Consent,
                ConsentHistory,
                HealthReserveAssessment,
            ):
                if model._meta.db_table not in existing_tables:
                    schema_editor.create_model(model)

        return old_config