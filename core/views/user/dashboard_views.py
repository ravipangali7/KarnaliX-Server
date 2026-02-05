"""
User Dashboard views.
"""
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Bet, WalletTransaction, ClientRequest, Bonus
from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def dashboard_stats(request):
    """
    Get dashboard statistics for User.
    """
    user = request.user
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    
    # Wallet info
    wallet_balance = user.wallet_balance
    exposure_balance = user.exposure_balance
    
    # Bet stats
    total_bets = Bet.objects.filter(user=user).count()
    pending_bets = Bet.objects.filter(user=user, result='PENDING').count()
    won_bets = Bet.objects.filter(user=user, result='WON').count()
    lost_bets = Bet.objects.filter(user=user, result='LOST').count()
    
    bet_stats = Bet.objects.filter(user=user).aggregate(
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    )
    
    # Recent bets
    recent_bets_count = Bet.objects.filter(user=user, placed_at__date__gte=last_7_days).count()
    
    # Transaction stats
    total_deposit = WalletTransaction.objects.filter(
        user=user, type='DEPOSIT'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdraw = WalletTransaction.objects.filter(
        user=user, type='WITHDRAW'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Pending requests
    pending_deposit = ClientRequest.objects.filter(
        user=user, request_type='DEPOSIT', status='PENDING'
    ).count()
    
    pending_withdraw = ClientRequest.objects.filter(
        user=user, request_type='WITHDRAW', status='PENDING'
    ).count()
    
    # Active bonuses
    active_bonuses = Bonus.objects.filter(user=user, status='ACTIVE').count()
    total_bonus = Bonus.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    
    return Response({
        'wallet': {
            'balance': str(wallet_balance),
            'exposure': str(exposure_balance),
            'available': str(wallet_balance - exposure_balance),
        },
        'bets': {
            'total': total_bets,
            'pending': pending_bets,
            'won': won_bets,
            'lost': lost_bets,
            'recent': recent_bets_count,
            'total_bet_amount': str(bet_stats['total_bet_amount'] or 0),
            'total_win_amount': str(bet_stats['total_win_amount'] or 0),
        },
        'transactions': {
            'total_deposit': str(total_deposit),
            'total_withdraw': str(total_withdraw),
            'pending_deposit': pending_deposit,
            'pending_withdraw': pending_withdraw,
        },
        'bonuses': {
            'active': active_bonuses,
            'total': str(total_bonus),
        },
        'vip_level': (user.settings or {}).get('vip_level', 'Gold'),
    })
