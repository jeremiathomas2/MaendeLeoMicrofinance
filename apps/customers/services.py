from django.db.models import Q


def build_customer_search(qs, q):
    return qs.filter(
        Q(full_name__icontains=q)
        | Q(phone__icontains=q)
        | Q(customer_number__icontains=q)
        | Q(national_id__icontains=q)
        | Q(email__icontains=q)
    )
