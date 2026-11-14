
import os

import requests
from django.core.exceptions import ValidationError


class MindGuardInferenceError(ValidationError):
    pass


def run_mindguard_inference(payload):
    """
    Send an assessment payload to the MindGuard ML service.

    The endpoint must be an HTTPS inference endpoint.
    """

    url = os.getenv("MINDGUARD_ML_URL", "").strip()

    if not url or not url.startswith("https://"):
        raise MindGuardInferenceError(
            "MindGuard ML HTTPS endpoint is not configured."
        )

    timeout = float(os.getenv("MINDGUARD_ML_TIMEOUT", "30"))

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # A private Cloud Run service requires a Google-signed
    # identity token. Do not use a static API secret as a
    # substitute for Cloud Run IAM authentication.
    if os.getenv("MINDGUARD_ML_AUTH", "private") == "private":
        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            audience = os.getenv(
                "MINDGUARD_ML_AUDIENCE", url.split("?")[0]
            )

            auth_request = google.auth.transport.requests.Request()
            token = google.oauth2.id_token.fetch_id_token(
                auth_request, audience
            )
            headers["Authorization"] = f"Bearer {token}"

        except Exception as exc:
            raise MindGuardInferenceError(
                "MindGuard ML authentication failed."
            ) from exc

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()

    except requests.Timeout as exc:
        raise MindGuardInferenceError(
            "MindGuard ML inference timed out."
        ) from exc

    except requests.RequestException as exc:
        raise MindGuardInferenceError(
            "MindGuard ML inference request failed."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise MindGuardInferenceError(
            "MindGuard ML returned invalid JSON."
        ) from exc

    if not isinstance(data, dict):
        raise MindGuardInferenceError(
            "Invalid MindGuard ML response."
        )

    if data.get("success") is not True:
        raise MindGuardInferenceError(
            "MindGuard ML inference was unsuccessful."
        )

    insight = data.get("result")

    if not isinstance(insight, dict):
        raise MindGuardInferenceError(
            "MindGuard ML returned an invalid insight."
        )

    delivery = insight.get("delivery")

    if not isinstance(delivery, dict):
        raise MindGuardInferenceError(
            "Missing MindGuard delivery controls."
        )

    if (
        delivery.get("automatic_alert") is not False
        or delivery.get("clinical_claim") is not False
    ):
        raise MindGuardInferenceError(
            "Unsafe MindGuard insight response."
        )

    return insight
