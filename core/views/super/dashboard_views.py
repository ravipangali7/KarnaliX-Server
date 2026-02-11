"""
Super Dashboard views.
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import User, WalletTransaction, ClientRequest, Bet, KYCVerification, SupportTicket, Bonus
from core.permissions import super_required
from django.db.models.functions import TruncDate


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

    last_30_days = today - timedelta(days=30)
    available_balance = user.wallet_balance
    total_master_balance = hierarchy_users.filter(role='MASTER').aggregate(total=Sum('wallet_balance'))['total'] or 0
    total_client_balance = hierarchy_users.filter(role='USER').aggregate(total=Sum('wallet_balance'))['total'] or 0
    total_active_user_balance = hierarchy_users.filter(role='USER', status='ACTIVE').aggregate(total=Sum('wallet_balance'))['total'] or 0
    # Users under masters in this hierarchy (clients of masters)
    master_child_ids = hierarchy_users.filter(parent__role='MASTER').values_list('id', flat=True)
    total_user_deposit_of_all_masters = ClientRequest.objects.filter(
        user_id__in=master_child_ids, request_type='DEPOSIT', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawal_of_all_masters = ClientRequest.objects.filter(
        user_id__in=master_child_ids, request_type='WITHDRAW', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_bonus_of_master = Bonus.objects.filter(user_id__in=master_child_ids).aggregate(total=Sum('amount'))['total'] or 0
    profit_loss_master = (Bet.objects.filter(user_id__in=master_child_ids).aggregate(total=Sum('bet_amount'))['total'] or 0) - (
        Bet.objects.filter(user_id__in=master_child_ids, result='WON').aggregate(total=Sum('win_amount'))['total'] or 0
    )
    chart_deposits = list(ClientRequest.objects.filter(user__in=hierarchy_users, request_type='DEPOSIT', status='APPROVED', created_at__date__gte=last_30_days).annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount')).order_by('day'))
    chart_withdrawals = list(ClientRequest.objects.filter(user__in=hierarchy_users, request_type='WITHDRAW', status='APPROVED', created_at__date__gte=last_30_days).annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount')).order_by('day'))
    dep_by_date = {item['day'].isoformat(): str(item['total']) for item in chart_deposits if item['day']}
    w_by_date = {item['day'].isoformat(): str(item['total']) for item in chart_withdrawals if item['day']}
    num_days = (today - last_30_days).days + 1
    chart_data_filled = [{'date': (last_30_days + timedelta(days=i)).isoformat(), 'deposits': dep_by_date.get((last_30_days + timedelta(days=i)).isoformat(), '0'), 'withdrawals': w_by_date.get((last_30_days + timedelta(days=i)).isoformat(), '0')} for i in range(num_days)]
    
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
            'available_balance': str(available_balance),
            'total_master_balance': str(total_master_balance),
            'total_client_balance': str(total_client_balance),
            'total_active_user_balance': str(total_active_user_balance),
            'total_user_deposit_of_all_masters': str(total_user_deposit_of_all_masters),
            'total_withdrawal_of_all_masters': str(total_withdrawal_of_all_masters),
            'total_bonus_of_master': str(total_bonus_of_master),
            'profit_loss_master': str(profit_loss_master),
        },
        'chart_data': chart_data_filled,
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
