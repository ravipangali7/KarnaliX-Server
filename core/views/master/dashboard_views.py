"""
Master Dashboard views.
"""
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import User, WalletTransaction, ClientRequest, Bet
from core.permissions import master_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def dashboard_stats(request):
    """
    Get dashboard statistics for Master.
    Only shows data for users directly under this Master.
    """
    user = request.user
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    
    # Get users directly under this Master
    if user.role in ['POWERHOUSE', 'SUPER']:
        hierarchy_users = User.objects.filter(role='USER')
    else:
        hierarchy_users = User.objects.filter(parent=user, role='USER')
    
    # User counts
    total_users = hierarchy_users.count()
    active_users = hierarchy_users.filter(status='ACTIVE').count()
    
    # New users
    new_users_today = hierarchy_users.filter(created_at__date=today).count()
    new_users_week = hierarchy_users.filter(created_at__date__gte=last_7_days).count()
    
    # Financial stats
    total_deposits = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='DEPOSIT', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='WITHDRAW', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_deposits = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='DEPOSIT', status='PENDING'
    ).count()
    
    pending_withdrawals = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='WITHDRAW', status='PENDING'
    ).count()
    
    # Bet stats
    total_bets = Bet.objects.filter(user__in=hierarchy_users).count()
    total_bet_amount = Bet.objects.filter(user__in=hierarchy_users).aggregate(total=Sum('bet_amount'))['total'] or 0
    total_win_amount = Bet.objects.filter(user__in=hierarchy_users, result='WON').aggregate(total=Sum('win_amount'))['total'] or 0
    
    # Total balance
    total_balance = hierarchy_users.aggregate(total=Sum('wallet_balance'))['total'] or 0
    
    # Own balance
    own_balance = user.wallet_balance
    
    return Response({
        'users': {
            'total_users': total_users,
            'active_users': active_users,
            'new_today': new_users_today,
            'new_this_week': new_users_week,
        },
        'financial': {
            'total_deposits': str(total_deposits),
            'total_withdrawals': str(total_withdrawals),
            'pending_deposits': pending_deposits,
            'pending_withdrawals': pending_withdrawals,
            'total_balance': str(total_balance),
            'own_balance': str(own_balance),
        },
        'bets': {
            'total_bets': total_bets,
            'total_bet_amount': str(total_bet_amount),
            'total_win_amount': str(total_win_amount),
            'profit_loss': str(total_bet_amount - total_win_amount),
        }
    })
