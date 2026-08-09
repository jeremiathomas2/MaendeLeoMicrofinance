from apps.credit.models import compute_score


def compute_and_store(assessment):
    """Compute the credit score and risk rating from the assessment data."""
    customer = assessment.application.customer
    assessment.credit_score = compute_score(assessment, customer)
    score = assessment.credit_score
    if score >= 80:
        assessment.risk_rating = 'LOW'
    elif score >= 60:
        assessment.risk_rating = 'MEDIUM'
    elif score >= 40:
        assessment.risk_rating = 'HIGH'
    else:
        assessment.risk_rating = 'CRITICAL'

    customer.credit_score = score
    customer.risk_rating = assessment.risk_rating
    customer.save(update_fields=['credit_score', 'risk_rating'])
    return assessment
