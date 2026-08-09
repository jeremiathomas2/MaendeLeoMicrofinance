"""Seed a complete MaendeLeo demo dataset (8 roles, branches, customers,
applications in every pipeline state, disbursed loans, repayments, savings,
teller sessions, journals, expenses and notifications).

Run:  python manage.py seed_demo
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounting import services as accounting_services
from apps.accounting.models import Expense
from apps.accounts.models import StaffProfile, User
from apps.accounts.roles import ALL_ROLES
from apps.cash_management import services as cash_services
from apps.cash_management.models import TellerSession
from apps.credit.models import CreditAssessment, CreditScoreComponent
from apps.customers.models import Customer, CustomerDocument, CustomerGroup, GroupMember
from apps.loans.models import LoanApplication, LoanProduct
from apps.loans import services as loan_services
from apps.notifications.models import notify
from apps.organization.models import Branch, Organization, SystemSetting
from apps.repayments.models import PaymentAllocationConfig
from apps.repayments import services as repayment_services
from apps.savings.models import SavingsProduct
from apps.savings import services as savings_services
from apps.workflows.models import ApprovalConfig

PASSWORD = 'demo@123'
TODAY = timezone.now().date()


class Command(BaseCommand):
    help = 'Seed the MaendeLeo MIS with a full demo dataset.'

    def handle(self, *args, **options):
        from django.db import transaction
        try:
            with transaction.atomic():
                self._run()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Seed failed (rolled back): {e}'))
            raise

    def _run(self):
        self.org = self._organization()
        self.branches = self._branches()
        self._settings()
        self._approval_config()
        self._credit_weights()
        self._allocation_config()
        accounting_services.coa()
        self.products = self._loan_products()
        self.savings_products = self._savings_products()
        self.groups = self._groups_and_permissions()
        self.users = self._users()
        self.customers = self._customers()
        self._groups_members()
        self._applications()
        self._savings()
        self._teller_sessions()
        self._expenses()
        self._journal()
        self._notifications()
        self.stdout.write(self.style.SUCCESS(
            'Seed complete. Login with any demo account (password: demo@123).'))

    # ------------------------------------------------------------- helpers

    def _organization(self):
        org, _ = Organization.objects.get_or_create(
            pk=1, defaults=dict(
                name='MaendeLeo Microfinance Limited',
                registration_number='MFI/TZ/2014/0319',
                address='Kariakoo Street 12, Dar es Salaam',
                phone='+255 22 210 1234',
                email='info@maendeleo.co.tz',
                website='https://www.maendeleo.co.tz',
                currency='TZS',
                financial_year_start=1,
            ))
        return org

    def _branches(self):
        rows = [
            ('DAR', 'Dar es Salaam', 'Coastal', 'Kariakoo Street 12'),
            ('ARI', 'Arusha', 'Northern', 'Sokoine Road 45'),
            ('MWZ', 'Mwanza', 'Lake Zone', 'Miti Mirefu Street 8'),
            ('DOD', 'Dodoma', 'Central', 'Miyuji Area'),
            ('MBY', 'Mbeya', 'Southern Highlands', 'Nane Nane Avenue'),
        ]
        branches = []
        for code, name, region, address in rows:
            b, _ = Branch.objects.get_or_create(code=code, defaults=dict(
                name=name, region=region, address=address,
                phone='+255 25 220 0000', email=f'{code.lower()}@maendeleo.co.tz',
                opening_date=date(2015, 1, 15), operating_hours='08:00 - 17:00',
            ))
            branches.append(b)
        return branches

    def _settings(self):
        defaults = [
            ('INSTITUTION', 'organization_name', 'Organization name', 'MaendeLeo Microfinance Limited'),
            ('INSTITUTION', 'currency', 'Currency', 'TZS'),
            ('LOANS', 'max_loan_term_months', 'Maximum loan term (months)', '24'),
            ('LOANS', 'auto_apply_penalties', 'Auto-apply penalties on overdue', 'Yes'),
            ('LOANS', 'default_purpose', 'Default loan purpose', ''),
            ('SAVINGS', 'minimum_opening_deposit', 'Minimum opening deposit', '5000'),
            ('SAVINGS', 'allow_dormant_activation', 'Allow dormant account activation', 'Yes'),
            ('PENALTIES', 'default_penalty_rate_per_day', 'Default penalty rate (%/day)', '1.00'),
            ('PENALTIES', 'penalty_grace_days', 'Penalty grace days', '3'),
            ('APPROVAL', 'branch_manager_limit', 'Branch Manager approval limit', '5000000'),
            ('APPROVAL', 'head_operations_limit', 'Head of Operations approval limit', '20000000'),
            ('APPROVAL', 'maker_checker_enforced', 'Enforce maker-checker', 'Yes'),
            ('ACCOUNTING', 'auto_post_journals', 'Auto-post journals from operations', 'Yes'),
            ('ACCOUNTING', 'financial_year_month', 'Financial year start month', '1'),
            ('NOTIFICATIONS', 'sms_enabled', 'SMS notifications enabled', 'No'),
            ('NOTIFICATIONS', 'email_enabled', 'Email notifications enabled', 'Yes'),
            ('SECURITY', 'password_min_length', 'Minimum password length', '8'),
            ('SECURITY', 'session_timeout_minutes', 'Session timeout (minutes)', '30'),
        ]
        for category, key, label, value in defaults:
            SystemSetting.objects.get_or_create(
                key=key, defaults=dict(label=label, value=value, category=category,
                                       description=f'Configures {label.lower()}.'))

    def _approval_config(self):
        rows = [
            ('Branch Manager', Decimal('0'), Decimal('5000000'), 1),
            ('Head of Operations', Decimal('5000000.01'), Decimal('20000000'), 2),
            ('General Manager', Decimal('20000000.01'), Decimal('99999999999.00'), 3),
        ]
        for role, low, high, prio in rows:
            ApprovalConfig.objects.get_or_create(role=role, defaults=dict(
                min_amount=low, max_amount=high, priority=prio))

    def _credit_weights(self):
        rows = [
            ('INCOME', 'Income Capacity', 20),
            ('REPAYMENT_HISTORY', 'Repayment History', 25),
            ('DEBT_RATIO', 'Debt Ratio', 20),
            ('BUSINESS_STABILITY', 'Business Stability', 15),
            ('COLLATERAL', 'Collateral', 10),
            ('CUSTOMER_HISTORY', 'Customer History', 10),
        ]
        for key, name, weight in rows:
            CreditScoreComponent.objects.get_or_create(
                key=key, defaults=dict(name=name, weight=weight))

    def _allocation_config(self):
        PaymentAllocationConfig.objects.get_or_create(
            pk=1, defaults=dict(order='penalty,fees,interest,principal'))

    def _loan_products(self):
        rows = [
            ('MBK', 'Micro-Business Loan', 100000, 5000000, '12.00', 'FLAT',
             'MONTHLY', 24, 0, 2.00, 1.00, 1.00, False, False,
             'Working capital for small retail and service businesses.'),
            ('UFA', 'Agricultural Loan', 200000, 10000000, '10.00', 'REDUCING_BALANCE',
             'MONTHLY', 24, 30, 1.50, 2.00, 1.00, True, False,
             'Seasonal crop and livestock financing with a grace period.'),
            ('SME', 'SME Growth Loan', 1000000, 50000000, '14.00', 'DECLINING',
             'MONTHLY', 36, 0, 1.00, 1.00, 1.50, True, False,
             'Expansion financing for established small and medium enterprises.'),
            ('SAC', 'Salary Advance', 100000, 3000000, '8.00', 'FLAT',
             'MONTHLY', 12, 0, 1.00, 0.00, 1.00, False, False,
             'Short-term advance against a verified salary.'),
        ]
        products = []
        for (code, name, low, high, rate, method, freq, term, grace,
             pfee, ifee, penalty, collateral, guarantor, desc) in rows:
            p, _ = LoanProduct.objects.get_or_create(code=code, defaults=dict(
                name=name, min_amount=Decimal(low), max_amount=Decimal(high),
                interest_rate=Decimal(rate), interest_method=method,
                repayment_frequency=freq, max_term_months=term,
                grace_period_days=grace, processing_fee=Decimal(pfee),
                insurance_fee=Decimal(ifee), penalty_rate=Decimal(penalty),
                collateral_required=collateral, guarantor_required=guarantor,
                description=desc))
            products.append(p)
        return products

    def _savings_products(self):
        rows = [
            ('SAV-VOL', 'Voluntary Savings', '3.00', 5000, 500, 5000),
            ('SAV-GRP', 'Group Savings', '5.00', 1000, 0, 1000),
            ('SAV-FXD', 'Fixed Deposit', '8.00', 500000, 0, 500000),
        ]
        products = []
        for code, name, rate, min_open, wfee, min_dep in rows:
            p, _ = SavingsProduct.objects.get_or_create(code=code, defaults=dict(
                name=name, interest_rate=Decimal(rate), interest_method='SIMPLE',
                minimum_opening_deposit=Decimal(min_open), withdrawal_fee=Decimal(wfee),
                minimum_balance=Decimal(min_dep),
                description=f'{name} product.'))
            products.append(p)
        return products

    def _perm(self, codename, model, name=None):
        ct = ContentType.objects.get_for_model(model)
        p, _ = Permission.objects.get_or_create(
            codename=codename, content_type=ct,
            defaults={'name': name or codename.replace('_', ' ').title()})
        return p

    def _groups_and_permissions(self):
        groups = {}
        for role in ALL_ROLES:
            g, _ = Group.objects.get_or_create(name=role)
            groups[role] = g

        see_all = self._perm('see_all_branches', Branch, 'See all branches')
        add_branch = self._perm('add_branch', Branch)
        change_setting = self._perm('change_systemsetting', SystemSetting)
        approve = self._perm('approve_loan', __import__('apps.loans.models', fromlist=['Loan']).Loan, 'Approve loans')
        disburse = self._perm('disburse_loan', __import__('apps.loans.models', fromlist=['Loan']).Loan, 'Disburse loans')
        assess = self._perm('perform_assessment', CreditAssessment, 'Perform credit assessments')
        reverse = self._perm('reverse_repayment', __import__('apps.repayments.models', fromlist=['Repayment']).Repayment, 'Reverse repayments')
        change_user = self._perm('change_user', User)
        reg = self._perm('register_customer', Customer)
        verify = self._perm('verify_customer_kyc', Customer)

        matrix = {
            'System Administrator': [see_all, add_branch, change_setting, approve, disburse,
                                     assess, reverse, change_user, reg, verify],
            'General Manager': [see_all, add_branch, change_setting, approve, disburse,
                                reverse, change_user, reg, verify],
            'Head of Operations': [see_all, change_setting, approve, disburse,
                                   reverse, change_user, reg, verify],
            'Branch Manager': [approve, disburse, reverse, reg, verify],
            'Credit Officer': [assess, reg],
            'Loan Officer': [reg],
            'Teller': [disburse],
            'Auditor': [see_all],
            'Accountant': [reverse, reg],
        }
        for role, perms in matrix.items():
            groups[role].permissions.set(perms)
        return groups

    def _user(self, username, role, first, last, branch, email_slug=None, superuser=False):
        u, created = User.objects.get_or_create(
            username=username,
            defaults=dict(first_name=first, last_name=last,
                          email=f'{email_slug or username}@maendeleo.co.tz',
                          employee_number=username.upper(),
                          is_staff=superuser, is_superuser=superuser,
                          phone='+255 700 000 000',
                          account_status=User.STATUS_ACTIVE))
        if created:
            u.set_password(PASSWORD)
            u.save()
        u.groups.add(self.groups[role])
        if not StaffProfile.objects.filter(user=u).exists():
            StaffProfile.objects.create(user=u, job_title=role,
                                        primary_branch=branch,
                                        employee_number=username.upper(),
                                        date_of_employment=date(2016, 6, 1))
        return u

    def _users(self):
        bm_ari = self.branches[1]
        return {
            'admin': self._user('admin', 'System Administrator', 'Grace', 'Mrema', self.branches[0], superuser=True),
            'general.manager': self._user('amina.kessy', 'General Manager', 'Amina', 'Kessy', self.branches[0]),
            'operations': self._user('joseph.msemo', 'Head of Operations', 'Joseph', 'Msemo', self.branches[0]),
            'bmanager.ari': self._user('peter.lema', 'Branch Manager', 'Peter', 'Lema', bm_ari),
            'bmanager.mwz': self._user('mariamu.juma', 'Branch Manager', 'Mariamu', 'Juma', self.branches[2]),
            'credit': self._user('fatuma.shirima', 'Credit Officer', 'Fatuma', 'Shirima', bm_ari),
            'loan': self._user('john.mrema', 'Loan Officer', 'John', 'Mrema', bm_ari),
            'loan.dar': self._user('elizabeth.kaaya', 'Loan Officer', 'Elizabeth', 'Kaaya', self.branches[0]),
            'teller': self._user('grace.mmasi', 'Teller', 'Grace', 'Mmasi', bm_ari),
            'teller.mwz': self._user('charles.sanga', 'Teller', 'Charles', 'Sanga', self.branches[2]),
            'auditor': self._user('edwin.mtui', 'Auditor', 'Edwin', 'Mtui', self.branches[0]),
            'accountant': self._user('sarah.njau', 'Accountant', 'Sarah', 'Njau', self.branches[0]),
        }

    def _customer(self, name, gender, phone, occupation, branch, income, expense,
                  employer='', nida='', risk='LOW'):
        number = self._next_cus(branch)
        c, created = Customer.objects.get_or_create(
            customer_number=number, defaults=dict(
                full_name=name, gender=gender, phone=phone, occupation=occupation,
                employer=employer or occupation, branch=branch,
                registered_by=self.users['loan'],
                monthly_income=Decimal(income), other_income=Decimal('0'),
                monthly_expenses=Decimal(expense),
                date_of_birth=date(1985, 5, 20),
                marital_status='MARRIED', address=f'{branch.name} area',
                national_id=nida,
                kyc_complete=True, kyc_verified_at=timezone.now(),
                risk_rating=risk, credit_score=72))
        if created:
            CustomerDocument.objects.create(
                customer=c, document_type=CustomerDocument.TYPE_NATIONAL_ID,
                uploaded_by=self.users['loan'], verification_status=CustomerDocument.STATUS_VERIFIED,
                verified_by=self.users['bmanager.ari'], verification_date=timezone.now(),
                notes='National ID verified during registration.')
        return c

    def _next_cus(self, branch):
        from apps.common.numbering import next_number
        return next_number('CUS', branch, include_year=False)

    def _customers(self):
        ari = self.branches[1]
        rows = [
            ('Neema Mahenge', 'FEMALE', '+255 712 100 001', 'Grocery store owner', ari, 1200000, 700000),
            ('Daudi Kimaro', 'MALE', '+255 713 100 002', 'Smallholder farmer', ari, 900000, 500000),
            ('Rehema Msaki', 'FEMALE', '+255 714 100 003', 'Tailor', ari, 1100000, 650000),
            ('Baraka Mushi', 'MALE', '+255 715 100 004', 'Electronics shop owner', ari, 1800000, 900000),
            ('Zainabu Kileo', 'FEMALE', '+255 716 100 005', 'Food vendor', ari, 800000, 450000),
            ('Issa Ramadhani', 'MALE', '+255 717 100 006', 'Boda boda operator', ari, 700000, 400000),
            ('Halima Omary', 'FEMALE', '+255 718 100 007', 'Salon owner', self.branches[2], 1000000, 600000),
            ('Joseph Kayombo', 'MALE', '+255 719 100 008', 'Carpenter', self.branches[2], 950000, 550000),
            ('Joyce Mwakalinga', 'FEMALE', '+255 720 100 009', 'School teacher', self.branches[0], 1500000, 700000),
            ('Erick Mushi', 'MALE', '+255 721 100 010', 'Truck driver', self.branches[0], 1300000, 800000),
            ('Anna Mwakasege', 'FEMALE', '+255 722 100 011', 'Poultry farmer', self.branches[3], 850000, 450000),
            ('Godfrey Mwakyusa', 'MALE', '+255 723 100 012', 'Retail shop owner', self.branches[4], 1050000, 620000),
        ]
        customers = []
        for idx, (name, gender, phone, occ, branch, inc, exp) in enumerate(rows):
            nida = f'1985-{idx + 1:08d}'
            customers.append(self._customer(name, gender, phone, occ, branch, inc, exp, nida=nida))
        return customers

    def _groups_members(self):
        ari = self.branches[1]
        g1, _ = CustomerGroup.objects.get_or_create(
            group_number='GRP-ARI-000001', defaults=dict(
                name='Tujijenge Business Group', branch=ari,
                formation_date=date(2025, 2, 10), meeting_location='Arusha Clock Tower',
                meeting_frequency='WEEKLY', meeting_day='Monday',
                created_by=self.users['loan']))
        for c in self.customers[:5]:
            GroupMember.objects.get_or_create(group=g1, customer=c,
                                              defaults={'role': GroupMember.ROLE_MEMBER})
        leader = self.customers[0]
        g1.leader = leader
        g1.save(update_fields=['leader'])
        GroupMember.objects.filter(group=g1, customer=leader).update(role=GroupMember.ROLE_LEADER)

        g2, _ = CustomerGroup.objects.get_or_create(
            group_number='GRP-MWZ-000001', defaults=dict(
                name='Ushirika Group', branch=self.branches[2],
                formation_date=date(2025, 4, 1), meeting_location='Mwanza Town Center',
                meeting_frequency='BIWEEKLY', meeting_day='Wednesday',
                created_by=self.users['loan']))
        for c in self.customers[6:8]:
            GroupMember.objects.get_or_create(group=g2, customer=c,
                                              defaults={'role': GroupMember.ROLE_MEMBER})

    # --------------------------------------------------------- loan pipeline

    def _application(self, customer, product, amount, term, purpose):
        from apps.common.numbering import next_number
        app = LoanApplication.objects.create(
            application_number=next_number('APP', customer.branch, include_year=True),
            customer=customer, branch=customer.branch, product=product,
            loan_officer=self.users['loan'], requested_amount=Decimal(amount),
            requested_term_months=term, purpose=purpose,
            status=LoanApplication.STATUS_DRAFT)
        return app

    def _assess(self, app, income, expenses, obligations, notes=''):
        assessment = CreditAssessment.objects.create(
            application=app, credit_officer=self.users['credit'],
            verified_income=Decimal(income), verified_expenses=Decimal(expenses),
            existing_obligations=Decimal(obligations),
            disposable_income=Decimal(income) - Decimal(expenses) - Decimal(obligations),
            recommendation=CreditAssessment.RECOMMEND_APPROVE,
            overall_notes=notes or 'Capacity and character verified in field visit.')
        from apps.credit.views_helpers import compute_and_store
        compute_and_store(assessment)
        app.status = LoanApplication.STATUS_RECOMMENDED
        app.save(update_fields=['status', 'updated_at'])
        return assessment

    def _applications(self):
        c = lambda i: self.customers[i]
        mbk, ufa, sme, sac = self.products
        lo, bm, credit = self.users['loan'], self.users['bmanager.ari'], self.users['credit']

        # Draft
        self._application(c(1), ufa, 1500000, 12, 'Buying seeds and fertilizer')

        # Submitted (pending credit assessment)
        app = self._application(c(0), mbk, 2000000, 12, 'Restocking grocery inventory')
        loan_services.submit_application(app, lo)

        # In credit assessment (assessed, recommended)
        app = self._application(c(3), mbk, 3000000, 18, 'Shop renovation and stock')
        loan_services.submit_application(app, lo)
        self._assess(app, 1800000, 900000, 150000)

        # Approved, awaiting disbursement
        app = self._application(c(5), sac, 1500000, 12, 'Buying a new motorcycle')
        loan_services.submit_application(app, lo)
        self._assess(app, 700000, 400000, 100000)
        loan_services.approve_application(app, bm, Decimal('1500000'), 'Approved at branch level.')

        # Rejected
        app = self._application(c(2), mbk, 4500000, 18, 'Expanding tailoring workshop')
        loan_services.submit_application(app, lo)
        self._assess(app, 1100000, 900000, 800000,
                     'Debt ratio too high for requested exposure.')
        app.status = LoanApplication.STATUS_REJECTED
        app.rejection_reason = 'High existing obligations relative to income.'
        app.save(update_fields=['status', 'rejection_reason', 'updated_at'])

        # Disbursed today — active loan
        app = self._application(c(4), mbk, 2500000, 12, 'Buying more stock for the food stall')
        loan_services.submit_application(app, lo)
        self._assess(app, 800000, 450000, 50000)
        loan_services.approve_application(app, bm, Decimal('2500000'))
        loan_services.disburse_loan(app, self.users['teller'], method='CASH')

        # Disbursed today — second active loan
        app = self._application(c(6), mbk, 1800000, 12, 'Salon equipment upgrade')
        loan_services.submit_application(app, lo)
        self._assess(app, 1000000, 600000, 100000)
        loan_services.approve_application(app, bm, Decimal('1800000'))
        loan_services.disburse_loan(app, self.users['teller.mwz'], method='CASH')

        # Disbursed 40 days ago with one overdue installment (PAR bucket)
        past = TODAY - timedelta(days=40)
        app = self._application(c(8), sac, 2000000, 12, 'Salary advance against June payslip')
        loan_services.submit_application(app, lo)
        self._assess(app, 1500000, 700000, 0)
        loan_services.approve_application(app, bm, Decimal('2000000'))
        loan = loan_services.disburse_loan(
            app, self.users['teller'], method='CASH',
            disbursement_date=TODAY - timedelta(days=70),
            first_installment_date=past)

        # A repayment today on the older loan
        repayment_services.receive_repayment(
            loan, self.users['teller'], Decimal('180000'), payment_date=TODAY,
            method='CASH')

        # A full installment repayment a few days ago on the first disbursed loan
        first_loan = LoanApplication.objects.get(
            application_number__endswith='-000006').loan
        repayment_services.receive_repayment(
            first_loan, self.users['teller'], Decimal('230000'),
            payment_date=TODAY - timedelta(days=2), method='CASH')

    # ------------------------------------------------------------- savings

    def _savings(self):
        vol, grp, fxd = self.savings_products
        teller = self.users['teller']
        pairs = [
            (self.customers[0], vol, 100000),
            (self.customers[1], grp, 40000),
            (self.customers[3], vol, 250000),
            (self.customers[4], grp, 60000),
            (self.customers[6], vol, 150000),
            (self.customers[9], fxd, 1000000),
        ]
        for customer, product, opening in pairs:
            account = savings_services.open_account(
                customer, product, teller, branch=customer.branch,
                opening_deposit=Decimal(opening))
            if customer.full_name == 'Neema Mahenge':
                savings_services.deposit(account, teller, Decimal('50000'),
                                         description='Weekly group savings top-up')

    # -------------------------------------------------------- teller & cash

    def _teller_sessions(self):
        teller, branch = self.users['teller'], self.branches[1]
        if not TellerSession.objects.filter(teller=teller, status='OPEN').exists():
            cash_services.open_session(teller, branch, Decimal('500000'))

        teller2, branch2 = self.users['teller.mwz'], self.branches[2]
        session = TellerSession.objects.filter(teller=teller2, status='CLOSED').first()
        if not session:
            session = cash_services.open_session(teller2, branch2, Decimal('300000'))
            session.opening_time = timezone.now() - timedelta(days=1)
            session.save(update_fields=['opening_time'])
            cash_services.reconcile_session(session, teller2, Decimal('1200000'))
            cash_services.close_session(session, teller2, Decimal('1200000'),
                                        variance_reason='')

    # -------------------------------------------------------------- expenses

    def _expenses(self):
        branch = self.branches[1]
        e1, _ = Expense.objects.get_or_create(
            reference='EXP-ARI-2026-000001', defaults=dict(
                category='Rent', vendor='Sokoine Property Ltd', branch=branch,
                amount=Decimal('3500000'), description='Branch rent for the quarter',
                requested_by=self.users['bmanager.ari'],
                approval_status=Expense.STATUS_PENDING))
        e2, _ = Expense.objects.get_or_create(
            reference='EXP-ARI-2026-000002', defaults=dict(
                category='Utilities', vendor='TANESCO', branch=branch,
                amount=Decimal('450000'), description='Electricity for July',
                requested_by=self.users['bmanager.ari'],
                approval_status=Expense.STATUS_APPROVED,
                approved_by=self.users['operations'],
                approved_at=timezone.now()))
        if e2.approval_status == Expense.STATUS_APPROVED:
            accounting_services.post_expense_entries(e2)

    # -------------------------------------------------------------- journal

    def _journal(self):
        from apps.accounting.models import JournalEntry
        if not JournalEntry.objects.filter(description='Opening capital injection').exists():
            accounts = accounting_services.coa()
            accounting_services.post_journal(
                'Opening capital injection',
                [
                    {'account': accounts['cash'], 'debit': Decimal('10000000'), 'credit': Decimal('0')},
                    {'account': accounts['equity'], 'debit': Decimal('0'), 'credit': Decimal('10000000')},
                ],
                branch=self.branches[0], user=self.users['admin'],
                source_type='Opening Balance')

    # ---------------------------------------------------------- notifications

    def _notifications(self):
        bm, lo = self.users['bmanager.ari'], self.users['loan']
        notify(bm, 'Loan awaiting your approval',
               'Application APP-ARI for Neema Mahenge is ready for approval.',
               'WARNING', link='/loans/')
        notify(lo, 'Repayment received', 'A repayment was recorded on a loan you manage.',
               'SUCCESS', link='/loans/')
        notify(lo, 'KYC review required', 'New customer documents need verification.',
               'INFO', link='/customers/')
        notify(self.users['credit'], 'Assessment queue', 'A submitted application is awaiting credit assessment.',
               'INFO', link='/loans/')
