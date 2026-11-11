from django.urls import path

from .views import (
    AssessmentSessionCreateView,
    AssessmentSessionCompleteView,
)

from waitlist.views import WaitlistRegistrationView


urlpatterns = [
    path(
        "sessions/",
        AssessmentSessionCreateView.as_view(),
        name="assessment-session-create",
    ),

    path(
        "sessions/<str:session_id>/complete/",
        AssessmentSessionCompleteView.as_view(),
        name="assessment-session-complete",
    ),   
    
    

]