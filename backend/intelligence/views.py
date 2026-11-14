
from rest_framework import generics, permissions
from rest_framework.response import Response

from intelligence.models import Insight
from consent.permissions import HasRequiredConsent
from mindguard.presentation import public_insight
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name="dispatch")
class MindGuardInsightListView(generics.GenericAPIView):
    """Retrieve saved MindGuard insights for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated, HasRequiredConsent]
    required_consent_type = "cognitive_assessment"

    def get(self, request):
        insights = (
            Insight.objects
            .filter(
                user=request.user,
                product_code="MINDGUARD",
            )
            .select_related("run")
            .prefetch_related("recommendations")
            .order_by("-generated_at")
        )

        results = [public_insight(insight, user_id=request.user.pk) for insight in insights]

        return Response({
            "product_code": "MINDGUARD",
            "count": len(results),
            "results": results,
        })
