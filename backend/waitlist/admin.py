from django.contrib import admin
from .models import WaitlistRegistration


@admin.register(WaitlistRegistration)
class WaitlistRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "full_name",
        "product_interest",
        "registration_status",
        "confirmation_email_status",
        "created_at",
    )
    search_fields = ("email", "full_name", "product_interest")
    list_filter = ("registration_status", "confirmation_email_status", "product_interest")
