"""Read-only Django-to-MindGuard ML integration."""

import json
import subprocess
from pathlib import Path
from hashlib import sha256

from django.core.exceptions import PermissionDenied, ValidationError

from assessments.models import AssessmentSession
from consent.models import Consent
from mindguard.models import CognitiveResult


BACKEND_DIR = Path(__file__).resolve().parents[1]
ML_DIR = BACKEND_DIR.parent / "ml"
ML_PYTHON = ML_DIR / "mlenv" / "Scripts" / "python.exe"
ML_WORKER = ML_DIR / "src" / "integration" / "worker.py"


def generate_mindguard_insight(*, user, session_id):
    """Generate a descriptive insight without database writes."""

    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required.")

    session = AssessmentSession.objects.filter(
        session_id=session_id,
        user=user,
        session_status="completed",
    ).first()

    if session is None:
        raise PermissionDenied(
            "Completed assessment not found for this user."
        )

    has_consent = Consent.objects.filter(
        user=user,
        consent_type="cognitive_assessment",
        status="granted",
    ).exists()

    if not has_consent:
        raise PermissionDenied("Current cognitive consent required.")

    result = CognitiveResult.objects.filter(
        session=session,
        user=user,
    ).first()

    if result is None:
        raise ValidationError("Assessment result is missing.")

     # Validate assessment accuracy before sending it to ML.
    # Dumosense stores accuracy as a fraction between 0 and 1.
    if result.accuracy_rate is None:
        raise ValidationError("Assessment accuracy is missing.")

    try:
        accuracy = float(result.accuracy_rate)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("Invalid assessment accuracy.") from exc

    if not 0 <= accuracy <= 1:
        raise ValidationError("Invalid assessment accuracy.")

    history = list(
        CognitiveResult.objects.filter(
            user=user,
            assessment_type__cognitive_domain=session.assessment_type.cognitive_domain,
            session__session_status="completed",
            calculated_at__lt=session.started_at,
            accuracy_rate__isnull=False,
        )
        .exclude(session=session)
        .order_by("calculated_at", "session_id")
        .values("accuracy_rate", "calculated_at")
    )

        # Validate historical accuracy values before ML processing.
    for item in history:
        try:
            historical_accuracy = float(item["accuracy_rate"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError(
                "Invalid historical assessment accuracy."
            ) from exc

        if not 0 <= historical_accuracy <= 1:
            raise ValidationError(
                "Invalid historical assessment accuracy."
            )

    record = {
        "user_id": str(user.pk),
        "run_id": "MG" + sha256(
            f"{session.session_id}|STAT_ENGINE_MVP_1.0".encode()
        ).hexdigest()[:18],
        "session_id": str(session.session_id),
        "model_version": "STAT_ENGINE_MVP_1.0",
        "index_time": result.calculated_at.isoformat(),
        "baseline_cutoff": session.started_at.isoformat(),
        "current_performance": {
            "accuracy": accuracy,
        },
        "baselines": {
            "per_domain": {"z": None},
        },
    }

    payload = {
        "history": [
            {
                "accuracy": float(item["accuracy_rate"]),
                "calculated_at": item["calculated_at"].isoformat(),
            }
            for item in history
        ],
        "record": record,
        "authenticated_user_id": str(user.pk),
        "consent_verified": True,
    }

    if not ML_PYTHON.is_file() or not ML_WORKER.is_file():
        raise ValidationError("MindGuard ML worker is unavailable.")

    try:
        completed = subprocess.run(
            [str(ML_PYTHON), str(ML_WORKER)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(
            "MindGuard ML worker could not complete."
        ) from exc

    if completed.returncode != 0:
        raise ValidationError("MindGuard ML worker rejected the request.")

    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError("Invalid response from MindGuard ML worker.") from exc

    if response.get("success") is not True:
        raise ValidationError("MindGuard ML worker returned an error.")

    insight = response["result"]

    if (
        insight.get("delivery", {}).get("automatic_alert") is not False
        or insight.get("delivery", {}).get("clinical_claim") is not False
    ):
        raise ValidationError("Unsafe MindGuard insight response.")

    return insight
