from django.db import models
from accounts.models import User


class IntelligenceRun(models.Model):
    run_id = models.CharField(max_length=20, primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="intelligence_runs",
        db_column="user_id",
    )

    product_code = models.CharField(max_length=30)
    triggered_at = models.DateTimeField()
    trigger_type = models.CharField(max_length=50)
    model_or_rule_version = models.CharField(max_length=100)

    input_start_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    input_end_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    run_status = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "intelligence_runs"

    def __str__(self):
        return f"{self.run_id} - {self.product_code}"


class Insight(models.Model):
    insight_id = models.CharField(max_length=20, primary_key=True)

    run = models.ForeignKey(
        IntelligenceRun,
        on_delete=models.PROTECT,
        related_name="insights",
        db_column="run_id",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="insights",
        db_column="user_id",
    )

    product_code = models.CharField(max_length=30)
    insight_type = models.CharField(max_length=100)
    insight_text = models.TextField()

    severity_or_priority = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    explanation_text = models.TextField(
        null=True,
        blank=True,
    )

    generated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "insights"

    def __str__(self):
        return f"{self.insight_id} - {self.insight_type}"


class Recommendation(models.Model):
    recommendation_id = models.CharField(max_length=20, primary_key=True)

    insight = models.ForeignKey(
        Insight,
        on_delete=models.PROTECT,
        related_name="recommendations",
        db_column="insight_id",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="recommendations",
        db_column="user_id",
    )

    product_code = models.CharField(max_length=30)
    recommendation_type = models.CharField(max_length=100)
    recommendation_text = models.TextField()

    priority = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "recommendations"

    def __str__(self):
        return f"{self.recommendation_id} - {self.recommendation_type}"


class Action(models.Model):
    action_id = models.CharField(max_length=20, primary_key=True)

    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.PROTECT,
        related_name="actions",
        db_column="recommendation_id",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="actions",
        db_column="user_id",
    )

    action_type = models.CharField(max_length=50)
    action_status = models.CharField(max_length=50)
    action_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "actions"

    def __str__(self):
        return f"{self.action_id} - {self.action_type}"

# Create your models here.
