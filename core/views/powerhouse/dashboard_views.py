"""Powerhouse dashboard: aggregates."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import User, UserRole, Deposit, Withdraw


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    pending_deposits = Deposit.objects.filter(status='pending').count()
    pending_withdrawals = Withdraw.objects.filter(status='pending').count()
    players = User.objects.filter(role=UserRole.PLAYER).count()
    masters = User.objects.filter(role=UserRole.MASTER).count()
    supers = User.objects.filter(role=UserRole.SUPER).count()
    total_balance = sum(
        (u.main_balance or 0) for u in User.objects.filter(role=UserRole.PLAYER)
    )
    return Response({
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'total_players': players,
        'total_masters': masters,
        'total_supers': supers,
        'total_balance': str(total_balance),
        'recent_deposits': [],
        'recent_withdrawals': [],
    })
