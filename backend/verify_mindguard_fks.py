from django.db import connection

tables = (
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
)

placeholders = ", ".join(["%s"] * len(tables))

query = f"""
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND REFERENCED_TABLE_NAME IS NOT NULL
  AND TABLE_NAME IN ({placeholders})
ORDER BY TABLE_NAME, COLUMN_NAME
"""

with connection.cursor() as cursor:
    cursor.execute(query, tables)
    relationships = cursor.fetchall()

for table, column, referenced_table, referenced_column in relationships:
    print(f"{table}.{column} -> {referenced_table}.{referenced_column}")

print(f"\nTotal foreign keys: {len(relationships)}")