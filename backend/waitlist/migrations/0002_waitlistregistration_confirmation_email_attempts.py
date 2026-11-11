from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("waitlist", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="waitlistregistration",
            name="confirmation_email_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
