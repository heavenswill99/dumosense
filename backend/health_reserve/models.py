from django.db import models
from accounts.models import User


class HealthReserveAssessment(models.Model):
    reserve_assessment_id = models.CharField(max_length=20, primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="health_reserve_assessments",
        db_column="user_id",
    )

    assessed_at = models.DateTimeField()

    healthcare_coverage_status = models.CharField(max_length=30)

    estimated_healthcare_exposure = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    emergency_health_resources = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    monthly_financial_obligations = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    number_of_dependants = models.IntegerField()

    current_preparedness_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    preparedness_target = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    preparedness_gap = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    preparedness_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=6,
    )

    reserve_status = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "health_reserve_assessments"

    def __str__(self):
        return self.reserve_assessment_id

# Create your models here.
