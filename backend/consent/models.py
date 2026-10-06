from django.db import models
from accounts.models import User

from django.db import models
from accounts.models import User


class Consent(models.Model):
    consent_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="consents",
        db_column="user_id"
    )

    consent_type = models.CharField(
        max_length=100
    )

    purpose = models.CharField(
        max_length=255
    )

    consent_version = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20
    )

    granted_at = models.DateTimeField()

    withdrawn_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = "consents"

    def __str__(self):
        return f"{self.consent_id} - {self.consent_type} - {self.status}"


class ConsentHistory(models.Model):
    consent_history_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    consent = models.ForeignKey(
        Consent,
        on_delete=models.PROTECT,
        related_name="history",
        db_column="consent_id"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="consent_history",
        db_column="user_id"
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    new_status = models.CharField(
        max_length=20
    )

    changed_at = models.DateTimeField()

    reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = "consent_history"

    def __str__(self):
        return f"{self.consent_history_id} - {self.previous_status} -> {self.new_status}"
