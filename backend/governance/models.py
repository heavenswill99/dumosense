from django.db import models
from accounts.models import User


class AuditLog(models.Model):
    audit_id = models.CharField(max_length=20, primary_key=True)

    actor_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        db_column="actor_user_id",
        null=True,
        blank=True,
    )

    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50)

    resource_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    timestamp = models.DateTimeField()
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "audit_logs"

    def __str__(self):
        return f"{self.audit_id} - {self.action}"

# Create your models here.
