from rest_framework.permissions import BasePermission

from .models import Consent


class HasRequiredConsent(BasePermission):
    message = "Required consent has not been granted."

    def has_permission(self, request, view):
        consent_type = getattr(view, "required_consent_type", None)

        if consent_type is None:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return Consent.objects.filter(
            user=request.user,
            consent_type=consent_type,
            status="granted",
        ).exists()