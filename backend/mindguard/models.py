from django.db import models
from accounts.models import User
from assessments.models import (
    AssessmentSession,
    AssessmentType,
    CognitiveTask,
)


class CognitiveResponse(models.Model):
    response_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    session = models.ForeignKey(
        AssessmentSession,
        on_delete=models.PROTECT,
        related_name="cognitive_responses",
        db_column="session_id"
    )

    task = models.ForeignKey(
        CognitiveTask,
        on_delete=models.PROTECT,
        related_name="cognitive_responses",
        db_column="task_id"
    )

    trial_number = models.IntegerField()

    stimulus_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    response_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    is_correct = models.IntegerField()

    reaction_time_ms = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    response_value = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    omission = models.IntegerField()

    recorded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cognitive_responses"

    def __str__(self):
        return f"{self.response_id} - Trial {self.trial_number}"


class CognitiveResult(models.Model):
    cognitive_result_id = models.CharField(
        max_length=20,
        primary_key=True
    )

    session = models.OneToOneField(
        AssessmentSession,
        on_delete=models.PROTECT,
        related_name="cognitive_result",
        db_column="session_id"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="cognitive_results",
        db_column="user_id"
    )

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="cognitive_results",
        db_column="assessment_type_id"
    )

    total_trials = models.IntegerField()

    correct_responses = models.IntegerField()

    incorrect_responses = models.IntegerField()

    omissions = models.IntegerField()

    accuracy_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True
    )

    mean_reaction_time_ms = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    median_reaction_time_ms = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    reaction_time_variability_ms = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    completion_time_seconds = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    difficulty_level = models.IntegerField(
        blank=True,
        null=True
    )

    baseline_difference = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        blank=True,
        null=True
    )

    previous_session_difference = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        blank=True,
        null=True
    )

    calculated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cognitive_results"

    def __str__(self):
        return f"{self.cognitive_result_id} - {self.session_id}"

# Create your models here.
