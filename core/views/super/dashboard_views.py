"""
Super Dashboard views.
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import User, WalletTransaction, ClientRequest, Bet, KYCVerification, SupportTicket
from core.permissions import super_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def dashboard_stats(request):
    """
    Get dashboard statistics for Super.
    Only shows data for users in their hierarchy.
    """
    user = request.user
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    
    # Get users in hierarchy (under this Super)
    if user.role == 'POWERHOUSE':
        hierarchy_users = User.objects.all()
    else:
        # Super can see masters they created and users under those masters
        hierarchy_users = User.objects.filter(
            Q(parent=user) | Q(parent__parent=user)
        )
    
    # User counts
    total_masters = hierarchy_users.filter(role='MASTER').count()
    total_users = hierarchy_users.filter(role='USER').count()
    active_users = hierarchy_users.filter(role='USER', status='ACTIVE').count()
    
    # New users
    new_users_today = hierarchy_users.filter(created_at__date=today).count()
    new_users_week = hierarchy_users.filter(created_at__date__gte=last_7_days).count()
    
    # Financial stats for hierarchy users
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
    
    # KYC stats
    pending_kyc = KYCVerification.objects.filter(user__in=hierarchy_users, status='PENDING').count()
    
    # Support stats
    open_tickets = SupportTicket.objects.filter(
        user__in=hierarchy_users, status__in=['OPEN', 'IN_PROGRESS']
    ).count()
    
    # Total balance
    total_balance = hierarchy_users.aggregate(total=Sum('wallet_balance'))['total'] or 0
    
    return Response({
        'users': {
            'total_masters': total_masters,
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
        },
        'bets': {
            'total_bets': total_bets,
            'total_bet_amount': str(total_bet_amount),
            'total_win_amount': str(total_win_amount),
            'profit_loss': str(total_bet_amount - total_win_amount),
        },
        'pending': {
            'kyc': pending_kyc,
            'support_tickets': open_tickets,
        }
    })
