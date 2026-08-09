"""Savings services: open account, deposit, withdraw (SRS sections 14-16)."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.audit.models import audit

ZERO = Decimal('0.00')


def open_account(customer, product, user, branch=None, opening_deposit=None):
    from apps.common.numbering import next_number

    branch = branch or getattr(user, 'staff_profile', None).primary_branch if hasattr(user, 'staff_profile') else branch
    if branch is None:
        branch = customer.branch

    account = SavingsAccount.objects.create(
        account_number=next_number('SAV', branch, include_year=False),
        customer=customer,
        product=product,
        branch=branch,
        opened_by=user,
    )
    if opening_deposit:
        deposit(account, user, opening_deposit, branch=branch, description='Opening deposit')
    audit(user, 'CUSTOMER_UPDATED', account, new={'opened': account.account_number})
    return account


@transaction.atomic
def deposit(account, user, amount, branch=None, description=''):
    from apps.common.numbering import next_number
    from apps.accounting.services import post_deposit_entries
    from apps.cash_management.models import CashTransaction

    amount = Decimal(amount)
    if amount <= 0:
        raise ValueError('Deposit amount must be positive')

    account = SavingsAccount.objects.select_for_update().get(pk=account.pk)
    branch = branch or account.branch

    txn = SavingsTransaction.objects.create(
        reference=next_number('TXN', branch, include_year=True),
        account=account,
        transaction_type=SavingsTransaction.TYPE_DEPOSIT,
        amount=amount,
        branch=branch,
        teller=user,
        created_by=user,
        description=description or 'Savings deposit',
    )
    account.balance += amount
    account.available_balance += amount
    account.save(update_fields=['balance', 'available_balance', 'updated_at'])

    CashTransaction.objects.create(
        reference=next_number('TXN', branch, include_year=True),
        transaction_type=CashTransaction.TYPE_DEPOSIT,
        amount=amount,
        branch=branch,
        teller=user,
        customer=account.customer,
        savings_account=account,
        transaction_date=timezone.now().date(),
        description=description or 'Savings deposit',
    )
    post_deposit_entries(txn)
    audit(user, 'SAVINGS_DEPOSIT', txn, new={'amount': str(amount)})
    return txn


@transaction.atomic
def withdraw(account, user, amount, branch=None, description=''):
    from apps.common.numbering import next_number
    from apps.accounting.services import post_withdrawal_entries
    from apps.cash_management.models import CashTransaction

    amount = Decimal(amount)
    if amount <= 0:
        raise ValueError('Withdrawal amount must be positive')

    account = SavingsAccount.objects.select_for_update().get(pk=account.pk)
    if amount > account.available_balance:
        raise ValueError('Insufficient available balance')
    if account.product.minimum_balance and account.balance - amount < account.product.minimum_balance:
        raise ValueError('Withdrawal would breach minimum balance')

    branch = branch or account.branch
    txn = SavingsTransaction.objects.create(
        reference=next_number('TXN', branch, include_year=True),
        account=account,
        transaction_type=SavingsTransaction.TYPE_WITHDRAWAL,
        amount=amount,
        branch=branch,
        teller=user,
        created_by=user,
        description=description or 'Savings withdrawal',
    )
    account.balance -= amount
    account.available_balance -= amount
    account.save(update_fields=['balance', 'available_balance', 'updated_at'])

    CashTransaction.objects.create(
        reference=next_number('TXN', branch, include_year=True),
        transaction_type=CashTransaction.TYPE_WITHDRAWAL,
        amount=amount,
        branch=branch,
        teller=user,
        customer=account.customer,
        savings_account=account,
        transaction_date=timezone.now().date(),
        description=description or 'Savings withdrawal',
    )
    post_withdrawal_entries(txn)
    audit(user, 'SAVINGS_WITHDRAWAL', txn, new={'amount': str(amount)})
    return txn
