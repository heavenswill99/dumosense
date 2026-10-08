from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import UserProfile, ProductEnrollment
from .serializers import UserProfileSerializer, ProductEnrollmentSerializer


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            UserProfile.objects.select_related("user"),
            user=self.request.user,
        )


class ProductEnrollmentListView(generics.ListAPIView):
    serializer_class = ProductEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductEnrollment.objects.filter(
            user=self.request.user
        ).order_by("enrolled_at")