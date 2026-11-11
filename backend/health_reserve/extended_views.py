
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .extended_models import FinancialProfiles, FamilyDependents
from .extended_serializers import (
    FinancialProfileSerializer, 
    FamilyDependentSerializer,
    
    )


class FinancialProfileListView(generics.ListAPIView):
    serializer_class = FinancialProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialProfiles.objects.filter(
            user=self.request.user
        ).order_by("-effective_from")

class FamilyDependentsListView(generics.ListAPIView):
    serializer_class = FamilyDependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FamilyDependents.objects.filter(
            user=self.request.user
        ).order_by("-effective_from")