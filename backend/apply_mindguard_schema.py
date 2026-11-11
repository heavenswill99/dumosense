from pathlib import Path
import re
import sqlparse

from django.db import connection

SQL_FILE = Path("sql/dumosense_mindguard_aiven_schema.sql")

EXPECTED_TABLES = [
    "assessment_types",
    "consents",
    "consent_history",
    "cognitive_tasks",
    "assessment_sessions",
    "cognitive_responses",
    "cognitive_results",
    "wellbeing_checkins",
    "context_records",
    "intelligence_runs",
    "insights",
    "recommendations",
    "actions",
]

sql = SQL_FILE.read_text(encoding="utf-8-sig")
statements = [
    s.strip()
    for s in sqlparse.split(sql)
    if sqlparse.format(s, strip_comments=True).strip()
]

table_pattern = re.compile(
    r"^CREATE\s+TABLE\s+`([a-z_]+)`\s*\(",
    re.IGNORECASE | re.DOTALL,
)

tables = []

for statement in statements:
    clean = sqlparse.format(statement, strip_comments=True).strip()
    match = table_pattern.match(clean)

    if not match:
        raise RuntimeError("Unexpected SQL statement. Stopping.")

    tables.append(match.group(1))

if tables != EXPECTED_TABLES:
    raise RuntimeError(
        f"Unexpected table list or creation order: {tables}"
    )

if "UNIQUE KEY uq_response_session_trial" not in sql:
    raise RuntimeError("Missing unique trial constraint.")

with connection.cursor() as cursor:
    existing = set(connection.introspection.table_names())

    conflicts = existing.intersection(EXPECTED_TABLES)
    if conflicts:
        raise RuntimeError(
            f"Tables already exist: {sorted(conflicts)}"
        )

    print("Database:", connection.settings_dict["NAME"])
    print("Tables to create:", len(tables))

    for table, statement in zip(tables, statements):
        print(f"Creating {table}...")
        cursor.execute(statement)
        print(f"Created {table}")

print("MindGuard schema deployment completed.")