from django.db import models
from django.utils import timezone


class WaitlistRegistration(models.Model):
    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    country = models.CharField(max_length=120, blank=True, null=True)
    employment_status = models.CharField(max_length=80, blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    product_interest = models.CharField(max_length=80)
    interest_reason = models.TextField(blank=True, null=True)
    testing_interest = models.CharField(max_length=80, blank=True, null=True)
    consent_accepted = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(default=timezone.now)
    consent_policy_version = models.CharField(max_length=50, default="v1")
    registration_status = models.CharField(max_length=20, default="pending")
    confirmation_email_status = models.CharField(max_length=20, default="pending")
    confirmation_email_attempts = models.PositiveSmallIntegerField(default=0)
    confirmation_email_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "waitlist_registrations"

    def __str__(self):
        return self.email
