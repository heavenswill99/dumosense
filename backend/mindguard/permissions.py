from rest_framework.permissions import BasePermission

from .models import MindGuardDataConsent


class HasMindGuardDataConsent(BasePermission):
    message = "Consent is required before saving MindGuard reflections."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and MindGuardDataConsent.objects.filter(
                user=request.user,
                granted=True,
            ).exists()
        )
