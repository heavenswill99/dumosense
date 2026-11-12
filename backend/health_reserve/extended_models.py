# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class FinancialProfiles(models.Model):
    financial_profile_id = models.CharField(primary_key=True, max_length=20)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    income_type = models.CharField(max_length=30)
    employment_status = models.CharField(max_length=30)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2)
    essential_monthly_expenses = models.DecimalField(max_digits=15, decimal_places=2)
    debt_repayments = models.DecimalField(max_digits=15, decimal_places=2)
    other_monthly_obligations = models.DecimalField(max_digits=15, decimal_places=2)
    existing_liquid_savings = models.DecimalField(max_digits=15, decimal_places=2)
    income_stability_index = models.DecimalField(max_digits=5, decimal_places=4)
    currency_code = models.CharField(max_length=3)
    country_code = models.CharField(max_length=2)
    region_code = models.CharField(max_length=100)
    recorded_at = models.DateTimeField()
    data_source = models.CharField(max_length=40)

    class Meta:
        managed = False
        db_table = 'financial_profiles'
        unique_together = (('user', 'effective_from'),)


class FinancialTransactions(models.Model):
    transaction_id = models.CharField(primary_key=True, max_length=20)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=20)
    category = models.CharField(max_length=60)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    source_type = models.CharField(max_length=40)
    is_recurring = models.CharField(max_length=10)
    recorded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'financial_transactions'


class HealthcareCostReference(models.Model):
    cost_reference_id = models.CharField(primary_key=True, max_length=20)
    country_code = models.CharField(max_length=2)
    region_code = models.CharField(max_length=100)
    service_category = models.CharField(max_length=60)
    care_setting = models.CharField(max_length=20)
    estimated_cost_low = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_cost_typical = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_cost_high = models.DecimalField(max_digits=15, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    source_name = models.CharField(max_length=100)
    source_date = models.DateField()
    valid_from = models.DateField()
    valid_to = models.DateField(blank=True, null=True)
    confidence_level = models.CharField(max_length=10)
    data_status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'healthcare_cost_reference'
        unique_together = (('country_code', 'region_code', 'service_category', 'care_setting', 'source_date'),)


class FamilyDependents(models.Model):
    dependent_id = models.CharField(primary_key=True, max_length=20)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    relationship = models.CharField(max_length=20)
    age_band = models.CharField(max_length=20)
    financial_dependency_level = models.CharField(max_length=10)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    recorded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'family_dependents'


class HealthReserveGoals(models.Model):
    goal_id = models.CharField(primary_key=True, max_length=20)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    product_enrollment = models.ForeignKey('accounts.ProductEnrollment', models.DO_NOTHING)
    recommended_target = models.DecimalField(max_digits=15, decimal_places=2)
    user_proposed_target = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    selected_target = models.DecimalField(max_digits=15, decimal_places=2)
    target_source = models.CharField(max_length=20)
    target_currency = models.CharField(max_length=3)
    target_date = models.DateField()
    goal_status = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    recommendation_run = models.ForeignKey('intelligence.IntelligenceRun', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'health_reserve_goals'


class HealthReserveActivity(models.Model):
    activity_id = models.CharField(primary_key=True, max_length=20)
    goal = models.ForeignKey(HealthReserveGoals, models.DO_NOTHING)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    activity_date = models.DateField()
    activity_type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    source_type = models.CharField(max_length=40)
    recorded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'health_reserve_activity'


class HealthReserveScenarios(models.Model):
    scenario_id = models.CharField(primary_key=True, max_length=20)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    goal = models.ForeignKey(HealthReserveGoals, models.DO_NOTHING)
    scenario_type = models.CharField(max_length=40)
    scenario_start_date = models.DateField()
    scenario_duration_months = models.SmallIntegerField()
    income_change_pct = models.DecimalField(max_digits=6, decimal_places=4)
    expense_change_pct = models.DecimalField(max_digits=6, decimal_places=4)
    healthcare_cost_assumption = models.DecimalField(max_digits=15, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    scenario_status = models.CharField(max_length=20)
    scenario_version = models.CharField(max_length=30)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'health_reserve_scenarios'


class HealthcareExposureItems(models.Model):
    exposure_item_id = models.CharField(primary_key=True, max_length=20)
    reserve_assessment = models.ForeignKey('health_reserve.HealthReserveAssessment', models.DO_NOTHING)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    cost_reference = models.ForeignKey(HealthcareCostReference, models.DO_NOTHING)
    dependent = models.ForeignKey(FamilyDependents, models.DO_NOTHING, blank=True, null=True)
    service_category = models.CharField(max_length=60)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    assumption_source = models.CharField(max_length=50)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'healthcare_exposure_items'


class HealthReserveContributionPlans(models.Model):
    plan_id = models.CharField(primary_key=True, max_length=20)
    goal = models.ForeignKey(HealthReserveGoals, models.DO_NOTHING)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    financial_profile = models.ForeignKey(FinancialProfiles, models.DO_NOTHING)
    choice_timestamp = models.DateTimeField()
    estimated_monthly_surplus = models.DecimalField(max_digits=15, decimal_places=2)
    rule_based_capacity_estimate = models.DecimalField(max_digits=15, decimal_places=2)
    system_suggested_monthly_contribution = models.DecimalField(max_digits=15, decimal_places=2)
    user_selected_monthly_contribution = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    contribution_currency = models.CharField(max_length=3)
    choice_status = models.CharField(max_length=20)
    plan_frequency = models.CharField(max_length=20)
    cashflow_coverage = models.CharField(max_length=30)
    data_source = models.CharField(max_length=40)
    plan_status = models.CharField(max_length=30)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'health_reserve_contribution_plans'


class HealthReserveAffordabilityOutcomes(models.Model):
    outcome_id = models.CharField(primary_key=True, max_length=20)
    plan = models.ForeignKey(HealthReserveContributionPlans, models.DO_NOTHING)
    user = models.ForeignKey('accounts.User', models.DO_NOTHING)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    expected_contribution = models.DecimalField(max_digits=15, decimal_places=2)
    reported_contribution = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    contribution_currency = models.CharField(max_length=3)
    reported_financial_strain = models.CharField(max_length=10)
    sustainability_status = models.CharField(max_length=25)
    adjustment_reason = models.CharField(max_length=50)
    observation_status = models.CharField(max_length=20)
    data_source = models.CharField(max_length=40)
    recorded_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'health_reserve_affordability_outcomes'
        unique_together = (('plan', 'review_period_start'),)
