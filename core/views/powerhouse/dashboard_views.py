"""
Powerhouse Dashboard views.
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import User, WalletTransaction, ClientRequest, Bet, KYCVerification, SupportTicket, Game, GameProvider
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def dashboard_stats(request):
    """
    Get dashboard statistics for Powerhouse.
    """
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # User counts
    total_supers = User.objects.filter(role='SUPER').count()
    total_masters = User.objects.filter(role='MASTER').count()
    total_users = User.objects.filter(role='USER').count()
    active_users = User.objects.filter(role='USER', status='ACTIVE').count()
    
    # New users
    new_users_today = User.objects.filter(created_at__date=today).count()
    new_users_week = User.objects.filter(created_at__date__gte=last_7_days).count()
    
    # Financial stats
    total_deposits = ClientRequest.objects.filter(
        request_type='DEPOSIT', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = ClientRequest.objects.filter(
        request_type='WITHDRAW', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_deposits = ClientRequest.objects.filter(
        request_type='DEPOSIT', status='PENDING'
    ).count()
    
    pending_withdrawals = ClientRequest.objects.filter(
        request_type='WITHDRAW', status='PENDING'
    ).count()
    
    # Bet stats
    total_bets = Bet.objects.count()
    total_bet_amount = Bet.objects.aggregate(total=Sum('bet_amount'))['total'] or 0
    total_win_amount = Bet.objects.filter(result='WON').aggregate(total=Sum('win_amount'))['total'] or 0
    won_count = Bet.objects.filter(result='WON').count()
    lost_count = Bet.objects.filter(result='LOST').count()
    pending_count = Bet.objects.filter(result='PENDING').count()
    today_bet_amount = Bet.objects.filter(placed_at__date=today).aggregate(total=Sum('bet_amount'))['total'] or 0
    
    # Games stats
    games_total = Game.objects.count()
    games_active = Game.objects.filter(status='ACTIVE').count()
    providers_count = GameProvider.objects.count()
    
    # KYC stats
    pending_kyc = KYCVerification.objects.filter(status='PENDING').count()
    kyc_approved = KYCVerification.objects.filter(status='APPROVED').count()
    kyc_rejected = KYCVerification.objects.filter(status='REJECTED').count()
    
    # Support stats
    open_tickets = SupportTicket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    support_open = SupportTicket.objects.filter(status='OPEN').count()
    support_in_progress = SupportTicket.objects.filter(status='IN_PROGRESS').count()
    
    # Total balance
    total_balance = User.objects.aggregate(total=Sum('wallet_balance'))['total'] or 0
    
    return Response({
        'users': {
            'total_supers': total_supers,
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
            'won_count': won_count,
            'lost_count': lost_count,
            'pending_count': pending_count,
            'today_bet_amount': str(today_bet_amount),
        },
        'games': {
            'total': games_total,
            'active': games_active,
            'providers': providers_count,
        },
        'kyc': {
            'pending': pending_kyc,
            'approved': kyc_approved,
            'rejected': kyc_rejected,
        },
        'support': {
            'open': support_open,
            'in_progress': support_in_progress,
            'open_tickets': open_tickets,
        },
        'pending': {
            'kyc': pending_kyc,
            'support_tickets': open_tickets,
        }
    })
