
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .extended_models import FinancialProfiles
from .extended_serializers import FinancialProfileSerializer


class FinancialProfileListView(generics.ListAPIView):
    serializer_class = FinancialProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialProfiles.objects.filter(
            user=self.request.user
        ).order_by("-effective_from")
