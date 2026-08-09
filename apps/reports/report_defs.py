"""Report definitions and generators (SRS section 52)."""

from decimal import Decimal

from apps.accounts.services import filter_by_scope
from apps.audit.models import AuditLog
from apps.customers.models import Customer
from apps.loans.models import Loan, LoanApplication
from apps.organization.models import Branch
from apps.repayments.models import Repayment

REPORT_CATEGORIES = {
    'customer': [
        ('register', 'Customer Register', 'fa-address-book', 'All registered customers'),
        ('new_customers', 'New Customers', 'fa-user-plus', 'Customers registered in a date range'),
        ('kyc', 'KYC Status', 'fa-id-card', 'Document verification status'),
    ],
    'loan': [
        ('applications', 'Loan Applications', 'fa-file-lines', 'All applications by status'),
        ('disbursed', 'Disbursed Loans', 'fa-hand-holding-dollar', 'Loans disbursed in a period'),
        ('outstanding', 'Outstanding Loans', 'fa-book', 'Loans with balances remaining'),
        ('written_off', 'Written-off Loans', 'fa-file-circle-xmark', 'Historical write-offs'),
    ],
    'repay': [
        ('daily_collections', 'Daily Collections', 'fa-calendar-day', 'Collections for a single day'),
        ('overdue', 'Overdue Repayments', 'fa-triangle-exclamation', 'Delinquent installments'),
        ('efficiency', 'Collection Efficiency', 'fa-percent', 'Due vs collected'),
    ],
    'portfolio': [
        ('par', 'PAR Aging Analysis', 'fa-layer-group', 'Portfolio at risk by bucket'),
        ('product', 'Product Performance', 'fa-boxes-stacked', 'Loans by product'),
        ('branch', 'Branch Performance', 'fa-code-branch', 'Per-branch portfolio health'),
    ],
    'acct': [
        ('trial_balance', 'Trial Balance', 'fa-scale-balanced', 'Debits vs credits'),
        ('income', 'Income Statement', 'fa-sack-dollar', 'Revenue and expenses'),
        ('balance', 'Balance Sheet', 'fa-building-columns', 'Assets, liabilities, equity'),
    ],
}


def _rows_for(kind, request, start, end, branch_id=None, product_id=None, status=None):
    user = request.user
    branch_qs = user.accessible_branches()
    rows = []

    if kind == 'register':
        qs = filter_by_scope(user, Customer.objects.all(), 'branch')
        if start: qs = qs.filter(created_at__date__gte=start)
        if end: qs = qs.filter(created_at__date__lte=end)
        if branch_id: qs = qs.filter(branch_id=branch_id)
        for c in qs[:200]:
            rows.append([c.customer_number, c.full_name, c.branch.name, c.phone, c.get_status_display(), c.risk_rating])

    elif kind == 'new_customers':
        qs = filter_by_scope(user, Customer.objects.all(), 'branch')
        if start: qs = qs.filter(created_at__date__gte=start)
        if end: qs = qs.filter(created_at__date__lte=end)
        if branch_id: qs = qs.filter(branch_id=branch_id)
        for c in qs[:200]:
            rows.append([c.created_at.date(), c.customer_number, c.full_name, c.branch.name, c.registered_by.get_full_name() if c.registered_by else '—'])

    elif kind == 'kyc':
        from apps.customers.models import CustomerDocument
        qs = CustomerDocument.objects.select_related('customer', 'verified_by').all()
        if branch_id: qs = qs.filter(customer__branch_id=branch_id)
        for d in qs[:200]:
            rows.append([d.customer.customer_number, d.customer.full_name, d.get_document_type_display(),
                         d.upload_date.date(), d.verified_by.get_full_name() if d.verified_by else '—',
                         d.get_verification_status_display()])

    elif kind == 'applications':
        qs = filter_by_scope(user, LoanApplication.objects.all(), 'branch')
        if status: qs = qs.filter(status=status)
        if start: qs = qs.filter(created_at__date__gte=start)
        if end: qs = qs.filter(created_at__date__lte=end)
        if branch_id: qs = qs.filter(branch_id=branch_id)
        if product_id: qs = qs.filter(product_id=product_id)
        for a in qs[:200]:
            rows.append([a.application_number, a.customer.full_name, a.product.name, str(a.requested_amount),
                         a.branch.name, a.loan_officer.get_full_name(), a.get_status_display()])

    elif kind == 'disbursed':
        qs = filter_by_scope(user, Loan.objects.all(), 'branch')
        if start: qs = qs.filter(disbursement_date__gte=start)
        if end: qs = qs.filter(disbursement_date__lte=end)
        if branch_id: qs = qs.filter(branch_id=branch_id)
        if product_id: qs = qs.filter(product_id=product_id)
        for l in qs[:200]:
            rows.append([l.loan_number, l.customer.full_name, l.product.name, str(l.principal),
                         l.disbursement_date, l.branch.name, l.get_status_display()])

    elif kind == 'outstanding':
        qs = filter_by_scope(user, Loan.objects.filter(status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']), 'branch')
        if branch_id: qs = qs.filter(branch_id=branch_id)
        if product_id: qs = qs.filter(product_id=product_id)
        for l in qs[:200]:
            rows.append([l.loan_number, l.customer.full_name, l.product.name, str(l.principal),
                         str(l.outstanding_principal), l.next_due_date, l.get_status_display()])

    elif kind == 'written_off':
        qs = filter_by_scope(user, Loan.objects.filter(status='WRITTEN_OFF'), 'branch')
        for l in qs[:200]:
            rows.append([l.loan_number, l.customer.full_name, str(l.principal), l.write_off_date, l.write_off_reason])

    elif kind == 'daily_collections':
        day = start or __import__('django.utils.timezone', fromlist=['now']).now().date()
        qs = filter_by_scope(user, Repayment.objects.filter(payment_date=day), 'branch')
        for r in qs[:200]:
            rows.append([r.receipt_number, r.customer.full_name, r.loan.loan_number, str(r.amount),
                         r.get_payment_method_display(), r.teller.get_full_name() if r.teller else '—', r.payment_date])

    elif kind == 'overdue':
        loans = filter_by_scope(user, Loan.objects.filter(status__in=['OVERDUE', 'PAR', 'DEFAULT']), 'branch')
        if branch_id: loans = loans.filter(branch_id=branch_id)
        for l in loans[:200]:
            inst = l.installments.filter(status__in=['PENDING', 'PARTIAL']).order_by('due_date').first()
            rows.append([l.loan_number, l.customer.full_name, l.branch.name, inst.due_date if inst else '—',
                         l.days_overdue, str(l.outstanding_principal), l.get_status_display()])

    elif kind == 'efficiency':
        for branch in branch_qs:
            due = Repayment.objects.filter(branch=branch).aggregate(s=__import__('django.db.models', fromlist=['Sum']).Sum('amount'))['s'] or Decimal('0')
            rows.append([branch.name, 'All periods', str(due)])

    elif kind == 'par':
        from apps.reports.services import par_tiers
        tiers = par_tiers()
        for key, label in [('current', 'Current (0 days)'), ('par_1_29', 'PAR 1-29'),
                           ('par_30_89', 'PAR 30-89'), ('par_90', 'PAR 90+')]:
            t = tiers[key]
            rows.append([label, t['count'], str(t['amount'])])

    elif kind == 'product':
        for product in Loan.objects.values('product__name', 'product_id').distinct():
            qs = Loan.objects.filter(product_id=product['product_id'], status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'])
            total = qs.aggregate(s=__import__('django.db.models', fromlist=['Sum']).Sum('outstanding_principal'))['s'] or Decimal('0')
            rows.append([product['product__name'], qs.count(), str(total)])

    elif kind == 'branch':
        for row in __import__('apps.reports.services', fromlist=['branch_performance']).branch_performance():
            rows.append([row['branch'].name, row['active_loans'], row['disbursed'], str(row['gross']), f'{row["par30_pct"]:.1f}%'])

    elif kind == 'trial_balance':
        from apps.accounting.services import trial_balance
        for r in trial_balance():
            rows.append([r['account'].code, r['account'].name, str(r['debit']), str(r['credit'])])

    elif kind == 'income':
        from apps.accounting.services import income_statement
        data = income_statement(start, end)
        for item in data['income']:
            rows.append([item['account'].name, 'Income', str(item['amount'])])
        for item in data['expense']:
            rows.append([item['account'].name, 'Expense', str(item['amount'])])
        rows.append(['Net income', 'Total', str(data['net_income'])])

    elif kind == 'balance':
        from apps.accounting.services import balance_sheet
        data = balance_sheet(as_of=end)
        for section in ('assets', 'liabilities', 'equity'):
            for account, amount in data['rows'][section]:
                rows.append([account.code, account.name, section.title(), str(amount)])
        rows.append(['', 'Total assets', '', str(data['assets'])])
        rows.append(['', 'Total liabilities + equity', '', str(data['liabilities'] + data['equity'])])

    return rows


HEADERS = {
    'register': ['Customer #', 'Name', 'Branch', 'Phone', 'Status', 'Risk'],
    'new_customers': ['Date', 'Customer #', 'Name', 'Branch', 'Registered By'],
    'kyc': ['Customer #', 'Name', 'Document', 'Uploaded', 'Verified By', 'Status'],
    'applications': ['App #', 'Customer', 'Product', 'Amount', 'Branch', 'Officer', 'Status'],
    'disbursed': ['Loan #', 'Customer', 'Product', 'Principal', 'Date', 'Branch', 'Status'],
    'outstanding': ['Loan #', 'Customer', 'Product', 'Principal', 'Outstanding', 'Next Due', 'Status'],
    'written_off': ['Loan #', 'Customer', 'Principal', 'Write-off Date', 'Reason'],
    'daily_collections': ['Receipt #', 'Customer', 'Loan #', 'Amount', 'Method', 'Teller', 'Date'],
    'overdue': ['Loan #', 'Customer', 'Branch', 'Next Due', 'Days Overdue', 'Outstanding', 'Status'],
    'efficiency': ['Branch', 'Period', 'Collected'],
    'par': ['Bucket', 'Loans', 'Outstanding'],
    'product': ['Product', 'Loans', 'Outstanding'],
    'branch': ['Branch', 'Active Loans', 'Disbursed', 'Gross', 'PAR30'],
    'trial_balance': ['Code', 'Account', 'Debit', 'Credit'],
    'income': ['Account', 'Type', 'Amount'],
    'balance': ['Code', 'Account', 'Section', 'Amount'],
}
