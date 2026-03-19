from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation
from django.db import transaction
from core.permissions import require_role
from core.models import User, UserRole, Transaction, TransactionActionType, TransactionWallet, TransactionType, TransactionStatus

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer(request):
    allowed_roles = [UserRole.POWERHOUSE, UserRole.SUPER, UserRole.MASTER, UserRole.PLAYER]
    err = require_role(request, allowed_roles)
    if err:
        return err

    if not request.user.check_password(request.data.get('password', '')):
        return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)

    username = str(request.data.get('username', '')).strip()
    if not username:
        return Response({'detail': 'Recipient username is required.'}, status=status.HTTP_400_BAD_REQUEST)

    to_user = User.objects.filter(username=username).first()
    if not to_user:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    if to_user.id == request.user.id:
        return Response({'detail': 'Cannot transfer to yourself.'}, status=status.HTTP_400_BAD_REQUEST)
    if to_user.role not in allowed_roles:
        return Response({'detail': 'Invalid recipient role.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = Decimal(str(request.data.get('amount', 0)))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        locked_users = User.objects.select_for_update().filter(id__in=[request.user.id, to_user.id]).in_bulk()
        sender = locked_users.get(request.user.id)
        receiver = locked_users.get(to_user.id)
        if sender is None or receiver is None:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        sender_before = sender.main_balance or Decimal('0')
        if sender_before < amount:
            return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)
        sender_after = sender_before - amount
        receiver_before = receiver.main_balance or Decimal('0')
        receiver_after = receiver_before + amount

        sender.main_balance = sender_after
        receiver.main_balance = receiver_after
        sender.save(update_fields=['main_balance'])
        receiver.save(update_fields=['main_balance'])

        Transaction.objects.create(
            user=sender,
            action_type=TransactionActionType.OUT,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            to_user=receiver,
            balance_before=sender_before,
            balance_after=sender_after,
            remarks='Transfer',
        )
        Transaction.objects.create(
            user=receiver,
            action_type=TransactionActionType.IN,
            wallet=TransactionWallet.MAIN_BALANCE,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            from_user=sender,
            balance_before=receiver_before,
            balance_after=receiver_after,
            remarks='Transfer',
        )

    return Response({'detail': 'OK'})
