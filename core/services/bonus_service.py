"""
Bonus application: welcome, first deposit, referral.
"""
from decimal import Decimal
from django.utils import timezone

from core.models import (
    User,
    BonusRule,
    BonusType,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def apply_welcome_bonus(user):
    """
    On registration: if active welcome BonusRule exists and user has a parent (master),
    apply bonus: deduct from parent main_balance, add to user bonus_balance.
    Create two transactions (parent out, user in).
    Returns (True, amount) if applied, (False, reason) otherwise.
    """
    rule = BonusRule.objects.filter(
        bonus_type=BonusType.WELCOME,
        is_active=True
    ).first()
    if not rule:
        return False, 'No active welcome bonus rule'
    if not user.parent:
        return False, 'Player has no parent master'
    parent = user.parent
    amount = rule.reward_amount
    if amount <= 0:
        return False, 'Invalid reward amount'
    if (parent.main_balance or Decimal('0')) < amount:
        return False, 'Parent has insufficient balance'
    # Deduct from parent main_balance
    parent.main_balance = (parent.main_balance or Decimal('0')) - amount
    parent.save(update_fields=['main_balance'])
    # Add to user bonus_balance
    user.bonus_balance = (user.bonus_balance or Decimal('0')) + amount
    user.save(update_fields=['bonus_balance'])
    # Transactions
    Transaction.objects.create(
        user=parent,
        action_type=TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.BONUS,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        to_user=user,
        remarks=f'Welcome bonus for {user.username}',
    )
    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.IN,
        wallet=TransactionWallet.BONUS_BALANCE,
        transaction_type=TransactionType.BONUS,
        amount=amount,
        status=TransactionStatus.SUCCESS,
        from_user=parent,
        remarks='Welcome bonus',
    )
    return True, amount
