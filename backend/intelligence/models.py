"""Mappings for existing intelligence tables. Tables are managed by SQL, not migrations."""
from django.db import models
from accounts.models import User

class IntelligenceRun(models.Model):
    run_id = models.CharField(max_length=20, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")
    product_code = models.CharField(max_length=30)
    triggered_at = models.DateTimeField()
    trigger_type = models.CharField(max_length=50)
    model_or_rule_version = models.CharField(max_length=100)
    input_start_date = models.DateTimeField(null=True, blank=True)
    input_end_date = models.DateTimeField(null=True, blank=True)
    run_status = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "intelligence_runs"

class Insight(models.Model):
    insight_id = models.CharField(max_length=20, primary_key=True)
    run = models.ForeignKey(IntelligenceRun, on_delete=models.PROTECT, db_column="run_id")
    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")
    product_code = models.CharField(max_length=30)
    insight_type = models.CharField(max_length=100)
    insight_text = models.TextField()
    severity_or_priority = models.CharField(max_length=20, null=True, blank=True)
    explanation_text = models.TextField(null=True, blank=True)
    generated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "insights"

class Recommendation(models.Model):
    recommendation_id = models.CharField(max_length=20, primary_key=True)
    insight = models.ForeignKey(Insight, on_delete=models.PROTECT, db_column="insight_id")
    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column="user_id")
    product_code = models.CharField(max_length=30)
    recommendation_type = models.CharField(max_length=100)
    recommendation_text = models.TextField()
    priority = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "recommendations"
