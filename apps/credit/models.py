from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel


class CreditScoreComponent(TimeStampedModel):
    """Configurable scoring weights (SRS section 22)."""

    KEY_INCOME = 'INCOME'
    KEY_REPAYMENT = 'REPAYMENT_HISTORY'
    KEY_DEBT = 'DEBT_RATIO'
    KEY_STABILITY = 'BUSINESS_STABILITY'
    KEY_COLLATERAL = 'COLLATERAL'
    KEY_HISTORY = 'CUSTOMER_HISTORY'

    key = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    weight = models.IntegerField(default=10, help_text='Percentage weight 0-100')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return f'{self.name} ({self.weight}%)'


class CreditAssessment(TimeStampedModel):
    RECOMMEND_APPROVE = 'APPROVE'
    RECOMMEND_REJECT = 'REJECT'
    RECOMMEND_CONDITIONAL = 'CONDITIONAL'
    RECOMMEND_CHOICES = [
        (RECOMMEND_APPROVE, 'Approve'),
        (RECOMMEND_REJECT, 'Reject'),
        (RECOMMEND_CONDITIONAL, 'Conditional approval'),
    ]

    RISK_LOW = 'LOW'
    RISK_MEDIUM = 'MEDIUM'
    RISK_HIGH = 'HIGH'
    RISK_CRITICAL = 'CRITICAL'
    RISK_CHOICES = [
        (RISK_LOW, 'Low'),
        (RISK_MEDIUM, 'Medium'),
        (RISK_HIGH, 'High'),
        (RISK_CRITICAL, 'Critical'),
    ]

    application = models.OneToOneField(
        'loans.LoanApplication', on_delete=models.CASCADE, related_name='credit_assessment',
    )
    credit_officer = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='credit_assessments',
    )
    verified_income = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    verified_expenses = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    existing_obligations = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    disposable_income = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    credit_score = models.IntegerField(default=0)
    risk_rating = models.CharField(max_length=12, choices=RISK_CHOICES, default=RISK_MEDIUM)
    recommendation = models.CharField(max_length=12, choices=RECOMMEND_CHOICES, default=RECOMMEND_APPROVE)
    recommended_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    recommended_term_months = models.IntegerField(null=True, blank=True)
    collateral_assessed = models.BooleanField(default=False)
    capacity_notes = models.TextField(blank=True)
    character_notes = models.TextField(blank=True)
    collateral_notes = models.TextField(blank=True)
    conditions_notes = models.TextField(blank=True)
    overall_notes = models.TextField(blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assessed_at']

    def __str__(self):
        return f'Assessment for {self.application.application_number}'


def compute_score(assessment, customer):
    """Compute a configurable 0-100 credit score from component weights.

    Each component is scored 0-100 then blended by its configured weight.
    """
    components = {c.key: c.weight for c in CreditScoreComponent.objects.filter(is_active=True)}
    total_weight = sum(components.values()) or 100

    def comp(key, score, default_weight=0):
        w = components.get(key, default_weight)
        return score * w

    income = float(customer.monthly_income + customer.other_income)
    expenses = float(customer.monthly_expenses)
    income_score = min(100, (income / max(expenses * 2.5, 1)) * 60) if income > 0 else 20

    debt = float(customer.existing_debts)
    debt_score = max(0, 100 - (debt / max(income, 1)) * 30) if income > 0 else 50

    score = (
        comp('INCOME', income_score, 20) +
        comp('DEBT_RATIO', debt_score, 20) +
        comp('REPAYMENT_HISTORY', 70, 25) +
        comp('BUSINESS_STABILITY', 60, 15) +
        comp('COLLATERAL', 70 if assessment.collateral_assessed else 30, 10) +
        comp('CUSTOMER_HISTORY', 60, 10)
    )
    return int(round(score / total_weight))
