
import csv
from pathlib import Path
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from accounts.models import User
from assessments.models import AssessmentType, AssessmentSession
from consent.models import Consent
from mindguard.models import CognitiveResult


DATA = DATA = Path.cwd().parent / "data" / "synthetic"

TARGETS = {
    "USR000427": "attention",
    "USR001152": "executive_function",
    "USR003931": "memory",
}


def load(name):
    with (DATA / f"{name}.csv").open(
        newline="", encoding="utf-8-sig"
    ) as file:
        return list(csv.DictReader(file))


def dt(value):
    if not value:
        return None

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            datetime_timezone.utc
        )

    return parsed


def convert(model, row):
    data = {}

    for field in model._meta.concrete_fields:
        if field.name in (
            "password",
            "last_login",
            "is_active",
            "is_staff",
        ):
            continue

        raw = row.get(field.column)

        if raw is None:
            continue

        if raw == "":
            if field.null:
                data[field.attname] = None
            continue

        field_type = field.get_internal_type()

        if field_type == "DateTimeField":
            value = dt(raw)
        elif field_type == "DecimalField":
            value = Decimal(raw)
        else:
            value = field.to_python(raw)

        data[field.attname] = value

    return data


def main():
    # Confirm the target database before writing.
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

    if database_name != "defaultdb":
        raise RuntimeError(
            f"Unexpected database: {database_name}"
        )

    print("Database verified:", database_name)

    users = {
        row["user_id"]: row
        for row in load("users")
    }

    types = {
        row["assessment_type_id"]: row
        for row in load("assessment_types")
    }

    consents = {
        row["consent_id"]: row
        for row in load("consents")
    }

    results = {
        row["session_id"]: row
        for row in load("cognitive_results")
    }

    sessions = []

    for row in load("assessment_sessions"):
        user_id = row["user_id"]

        if user_id not in TARGETS:
            continue

        if row["session_status"] != "completed":
            continue

        result = results.get(row["session_id"])

        if result is None:
            continue

        assessment_type = types.get(
            row["assessment_type_id"]
        )

        if assessment_type is None:
            continue

        if (
            assessment_type["cognitive_domain"]
            != TARGETS[user_id]
        ):
            continue

        consent = consents.get(row["consent_id"])

        if not consent:
            continue

        if consent["user_id"] != user_id:
            continue

        if consent["consent_type"] != "cognitive_assessment":
            continue

        if consent["status"] != "granted":
            continue

        if (
            result["user_id"] != user_id
            or result["assessment_type_id"]
            != row["assessment_type_id"]
        ):
            raise ValueError(
                f"Result relationship mismatch: {row['session_id']}"
            )

        sessions.append(row)

    selected_user_ids = {
        row["user_id"] for row in sessions
    }

    selected_type_ids = {
        row["assessment_type_id"] for row in sessions
    }

    selected_consent_ids = {
        row["consent_id"] for row in sessions
    }

    # Check that all three intended users were selected.
    if selected_user_ids != set(TARGETS):
        raise RuntimeError(
            "Not all three synthetic users have valid sessions."
        )

    # Require at least four sessions per target domain.
    for user_id in TARGETS:
        count = sum(
            row["user_id"] == user_id
            for row in sessions
        )

        if count < 4:
            raise RuntimeError(
                f"Insufficient sessions for {user_id}: {count}"
            )

    print("Selected users:", sorted(selected_user_ids))
    print("Selected sessions:", len(sessions))
    print("Selected consents:", len(selected_consent_ids))

    # Check all imported IDs for collisions before writing.
    checks = (
        (User, selected_user_ids),
        (Consent, selected_consent_ids),
        (
            AssessmentSession,
            {row["session_id"] for row in sessions},
        ),
        (
            CognitiveResult,
            {
                results[row["session_id"]]["cognitive_result_id"]
                for row in sessions
            },
        ),
    )

    for model, ids in checks:
        if model.objects.filter(pk__in=ids).exists():
            raise RuntimeError(
                f"Existing records detected in {model.__name__}. "
                "Import cancelled."
            )

    with transaction.atomic():
        # Assessment types must exist before sessions.
        for type_id in sorted(selected_type_ids):
            AssessmentType.objects.get_or_create(
                pk=type_id,
                defaults=convert(
                    AssessmentType,
                    types[type_id],
                ),
            )

        # Create synthetic users with unusable passwords.
        for user_id in sorted(selected_user_ids):
            user = User(
                **convert(User, users[user_id])
            )

            user.set_unusable_password()
            user.is_active = True
            user.is_staff = False
            user.save()

        # Create consent records.
        for consent_id in sorted(selected_consent_ids):
            Consent.objects.create(
                **convert(
                    Consent,
                    consents[consent_id],
                )
            )

        # Import assessments in chronological order.
        sessions.sort(
            key=lambda row: row["started_at"]
        )

        for row in sessions:
            AssessmentSession.objects.create(
                **convert(AssessmentSession, row)
            )

            CognitiveResult.objects.create(
                **convert(
                    CognitiveResult,
                    results[row["session_id"]],
                )
            )

    print("IMPORT SUCCESSFUL")
    print("Users imported:", len(selected_user_ids))
    print("Consents imported:", len(selected_consent_ids))
    print("Assessment sessions imported:", len(sessions))
    print("Cognitive results imported:", len(sessions))
    print("Existing accounts were not modified.")


if __name__ == "__main__":
    main()
