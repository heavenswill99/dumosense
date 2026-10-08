from django.urls import path

from .views import (
    CognitiveResponseCreateView,
    CognitiveResultDetailView,
    CognitiveResultListView,
    WellbeingCheckinCreateView,
    ContextRecordCreateView,
    WellbeingCheckinListView,
    ContextRecordListView
)


urlpatterns = [
    path(
        "sessions/<str:session_id>/responses/",
        CognitiveResponseCreateView.as_view(),
        name="cognitive-response-create",
    ),
    path(
        "results/",
        CognitiveResultListView.as_view(),
        name="cognitive-result-list",
    ),
    path(
        "results/<str:cognitive_result_id>/",
        CognitiveResultDetailView.as_view(),
        name="cognitive-result-detail",
    ),

    path(
    "wellbeing/checkins/",
    WellbeingCheckinCreateView.as_view(),
    name="wellbeing-checkin-create",
    ),

    path(
    "context/",
    ContextRecordCreateView.as_view(),
    name="context-record-create",
    ),

    path(
    "wellbeing/history/",
    WellbeingCheckinListView.as_view(),
    name="wellbeing-checkin-list",
    ),

    path(
    "context/history/",
    ContextRecordListView.as_view(),
    name="context-history",
    ),


]