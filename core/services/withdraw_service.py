"""Withdraw approval: user deducted, parent added. Player must have at least one approved payment mode (parent's)."""
from decimal import Decimal
from django.utils import timezone
from core.models import (
    UserRole,
    PaymentMode,
    Withdraw,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def approve_withdraw(withdrawal, processed_by, pin=None, use_password=False):
    user = withdrawal.user
    amount = withdrawal.amount
    if user.role == UserRole.SUPER and processed_by.role == UserRole.POWERHOUSE:
        if (user.main_balance or Decimal('0')) < amount:
            return False, 'Insufficient balance'
        user.main_balance = (user.main_balance or Decimal('0')) - amount
        user.save(update_fields=['main_balance'])
        withdrawal.status = 'approved'
        withdrawal.processed_by = processed_by
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'processed_by', 'processed_at'])
        Transaction.objects.create(
            user=user,
            action_type=TransactionActionType.OUT,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.WITHDRAW,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            remarks='Withdraw approved',
        )
        return True, None
    parent = user.parent
    if not parent:
        return False, 'User has no parent'
    if user.role == UserRole.PLAYER:
        if not PaymentMode.objects.filter(user=parent, status='approved').exists():
            return False, 'At least one payment method must be approved before withdrawal.'
    if (user.main_balance or Decimal('0')) < amount:
        return False, 'Insufficient balance'
    user.main_balance = (user.main_balance or Decimal('0')) - amount
    user.save(update_fields=['main_balance'])
    parent.main_balance = (parent.main_balance or Decimal('0')) + amount
    parent.save(update_fields=['main_balance'])
    withdrawal.status = 'approved'
    withdrawal.processed_by = processed_by
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=['status', 'processed_by', 'processed_at'])
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.WITHDRAW,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        remarks='Withdraw approved',
    )
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.WITHDRAW,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=user,
        remarks='Withdraw from ' + user.username,
    )
    return True, None
