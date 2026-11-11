from django.urls import path
from .extended_views import FinancialProfileListView, FamilyDependentsListView

from .views import (
    HealthReserveAssessmentListView,
    HealthReserveAssessmentCreateView,
    HealthReserveProgressView,
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
    path(
        "progress/",
        HealthReserveProgressView.as_view(),
        name="health-reserve-progress",
    ),

    path(
    "financial-profile/",
    FinancialProfileListView.as_view(),
    name="health-reserve-financial-profile",
    ),

    path(
    "family-dependents/",
    FamilyDependentsListView.as_view(),
    name="health-reserve-family-dependents",
    ),
]