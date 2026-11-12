from django.db import models
from accounts.models import User
from consent.models import Consent


class AssessmentType(models.Model):
    assessment_type_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    assessment_name = models.CharField(
        max_length=100
    )

    cognitive_domain = models.CharField(
        max_length=50
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    active = models.IntegerField()

    class Meta:
        managed = False
        db_table = "assessment_types"

    def __str__(self):
        return f"{self.assessment_name} - {self.cognitive_domain}"


class CognitiveTask(models.Model):
    task_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="cognitive_tasks",
        db_column="assessment_type_id"
    )

    task_name = models.CharField(
        max_length=100
    )

    task_type = models.CharField(
        max_length=50
    )

    default_difficulty = models.IntegerField()

    active = models.IntegerField()

    class Meta:
        managed = False
        db_table = "cognitive_tasks"

    def __str__(self):
        return f"{self.task_name} - {self.task_type}"


class AssessmentSession(models.Model):
    session_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="assessment_sessions",
        db_column="user_id"
    )

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="sessions",
        db_column="assessment_type_id"
    )

    started_at = models.DateTimeField()

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    session_status = models.CharField(
        max_length=20
    )

    difficulty_level = models.IntegerField()

    device_type = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    consent = models.ForeignKey(
        Consent,
        on_delete=models.PROTECT,
        related_name="assessment_sessions",
        db_column="consent_id"
    )

    class Meta:
        managed = False
        db_table = "assessment_sessions"

    def __str__(self):
        return f"{self.session_id} - {self.session_status}"

