"""
Deposit approval: parent main_balance deducted, user main_balance added.
Dual transactions. Powerhouse: only adjust super balance (no parent deduction).
"""
from decimal import Decimal
from django.utils import timezone

from core.models import (
    User,
    UserRole,
    Deposit,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def approve_deposit(deposit, processed_by, pin=None, use_password=False):
    """
    Approve a deposit. For powerhouse->super: only add to super. For others: deduct parent, add to user.
    Returns (True, None) or (False, error_message).
    """
    user = deposit.user
    amount = deposit.amount
    if user.role == UserRole.SUPER and processed_by.role == UserRole.POWERHOUSE:
        user.main_balance = (user.main_balance or Decimal('0')) + amount
        user.save(update_fields=['main_balance'])
        deposit.status = 'approved'
        deposit.processed_by = processed_by
        deposit.processed_at = timezone.now()
        deposit.save(update_fields=['status', 'processed_by', 'processed_at'])
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.IN,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            remarks=f'Deposit #{deposit.pk} approved',
        )
        return True, None
    parent = user.parent
    if not parent:
        return False, 'User has no parent'
    if (parent.main_balance or Decimal('0')) < amount:
        return False, 'Parent has insufficient balance'
    parent.main_balance = (parent.main_balance or Decimal('0')) - amount
    parent.save(update_fields=['main_balance'])
    user.main_balance = (user.main_balance or Decimal('0')) + amount
    user.save(update_fields=['main_balance'])
    deposit.status = 'approved'
    deposit.processed_by = processed_by
    deposit.processed_at = timezone.now()
    deposit.save(update_fields=['status', 'processed_by', 'processed_at'])
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.DEPOSIT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        to_user=user,
        remarks=f'Deposit #{deposit.pk} for {user.username}',
    )
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.DEPOSIT,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=parent,
        remarks=f'Deposit #{deposit.pk} approved',
    )
    return True, None
