from django.db import models
from accounts.models import User


class Event(models.Model):
    event_id = models.CharField(max_length=20, primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="events",
        db_column="user_id",
    )

    event_type = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    source = models.CharField(max_length=50)

    related_entity_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    related_entity_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "events"

    def __str__(self):
        return f"{self.event_id} - {self.event_type}"

# Create your models here.
