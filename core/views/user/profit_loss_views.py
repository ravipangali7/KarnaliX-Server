"""
User views for Profit/Loss.
"""
from django.db.models import Sum, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Bet
from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def profit_loss(request):
    """
    Get profit/loss summary for current user.
    """
    user = request.user
    
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    bets = Bet.objects.filter(user=user)
    
    if date_from:
        bets = bets.filter(placed_at__date__gte=date_from)
    if date_to:
        bets = bets.filter(placed_at__date__lte=date_to)
    
    # Overall stats
    overall = bets.aggregate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    )
    
    total_bet = overall['total_bet_amount'] or 0
    total_win = overall['total_win_amount'] or 0
    
    # Stats by game type
    by_game_type = bets.values('game__game_type').annotate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    ).order_by('game__game_type')
    
    game_type_stats = []
    for stat in by_game_type:
        bet_amount = stat['total_bet_amount'] or 0
        win_amount = stat['total_win_amount'] or 0
        game_type_stats.append({
            'game_type': stat['game__game_type'],
            'total_bets': stat['total_bets'],
            'total_bet_amount': str(bet_amount),
            'total_win_amount': str(win_amount),
            'profit_loss': str(win_amount - bet_amount),
        })
    
    # Stats by result
    won_stats = bets.filter(result='WON').aggregate(
        count=Count('id'),
        bet_amount=Sum('bet_amount'),
        win_amount=Sum('win_amount')
    )
    
    lost_stats = bets.filter(result='LOST').aggregate(
        count=Count('id'),
        bet_amount=Sum('bet_amount')
    )
    
    return Response({
        'overall': {
            'total_bets': overall['total_bets'] or 0,
            'total_bet_amount': str(total_bet),
            'total_win_amount': str(total_win),
            'profit_loss': str(total_win - total_bet),
            'roi': str(round(((total_win - total_bet) / total_bet * 100), 2) if total_bet > 0 else 0),
        },
        'by_game_type': game_type_stats,
        'by_result': {
            'won': {
                'count': won_stats['count'] or 0,
                'bet_amount': str(won_stats['bet_amount'] or 0),
                'win_amount': str(won_stats['win_amount'] or 0),
            },
            'lost': {
                'count': lost_stats['count'] or 0,
                'bet_amount': str(lost_stats['bet_amount'] or 0),
            },
            'pending': bets.filter(result='PENDING').count(),
        }
    })
