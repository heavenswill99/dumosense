from django.urls import path

from .views import WaitlistRegistrationView

urlpatterns = [
    path("", WaitlistRegistrationView.as_view(), name="waitlist-registration"),
]
