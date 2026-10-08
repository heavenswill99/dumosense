from django.urls import path

from .views import (
    HealthReserveAssessmentListView,
    HealthReserveAssessmentCreateView,
)

urlpatterns = [
    path(
        "assessments/",
        HealthReserveAssessmentListView.as_view(),
        name="health-reserve-assessments",
    ),
    path(
        "assessments/create/",
        HealthReserveAssessmentCreateView.as_view(),
        name="health-reserve-assessment-create",
    ),
]