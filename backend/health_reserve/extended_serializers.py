
from rest_framework import serializers

from .extended_models import FinancialProfiles, FamilyDependents


class FinancialProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProfiles

        fields = [
            "financial_profile_id",
            "effective_from",
            "effective_to",
            "income_type",
            "employment_status",
            "monthly_income",
            "essential_monthly_expenses",
            "debt_repayments",
            "other_monthly_obligations",
            "existing_liquid_savings",
            "income_stability_index",
            "currency_code",
            "country_code",
            "region_code",
            "recorded_at",
            "data_source",
        ]

        read_only_fields = fields


class FamilyDependentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyDependents

        fields = [
            "dependent_id",
            "relationship",
            "age_band",
            "financial_dependency_level",
            "effective_from",
            "effective_to",
            "recorded_at",
        ]

        read_only_fields = fields