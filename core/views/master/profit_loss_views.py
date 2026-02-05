"""
Master views for Profit/Loss reports.
"""
from django.db.models import Sum, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import User, Bet, Game
from core.serializers.game_serializers import BetSerializer
from core.permissions import master_required


def get_hierarchy_users(user):
    """Get users under this Master."""
    if user.role in ['POWERHOUSE', 'SUPER']:
        return User.objects.filter(role='USER')
    else:
        return User.objects.filter(parent=user, role='USER')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def profit_loss_sports(request):
    """
    Get profit/loss report by sports/game type.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    game_type = request.query_params.get('game_type')
    
    bets = Bet.objects.filter(user__in=hierarchy_users)
    
    if date_from:
        bets = bets.filter(placed_at__date__gte=date_from)
    if date_to:
        bets = bets.filter(placed_at__date__lte=date_to)
    if game_type:
        bets = bets.filter(game__game_type=game_type)
    
    # Group by game type
    stats_by_type = bets.values('game__game_type').annotate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    ).order_by('game__game_type')
    
    result = []
    for stat in stats_by_type:
        bet_amount = stat['total_bet_amount'] or 0
        win_amount = stat['total_win_amount'] or 0
        result.append({
            'game_type': stat['game__game_type'],
            'total_bets': stat['total_bets'],
            'total_bet_amount': str(bet_amount),
            'total_win_amount': str(win_amount),
            'profit_loss': str(bet_amount - win_amount),
        })
    
    # Total summary
    total = bets.aggregate(
        total_bets=Count('id'),
        total_bet=Sum('bet_amount'),
        total_win=Sum('win_amount')
    )
    
    return Response({
        'by_game_type': result,
        'summary': {
            'total_bets': total['total_bets'] or 0,
            'total_bet_amount': str(total['total_bet'] or 0),
            'total_win_amount': str(total['total_win'] or 0),
            'profit_loss': str((total['total_bet'] or 0) - (total['total_win'] or 0)),
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def profit_loss_client(request):
    """
    Get profit/loss report by client (user).
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    bets = Bet.objects.filter(user__in=hierarchy_users)
    
    if date_from:
        bets = bets.filter(placed_at__date__gte=date_from)
    if date_to:
        bets = bets.filter(placed_at__date__lte=date_to)
    
    # Group by user
    stats_by_user = bets.values('user__id', 'user__username').annotate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    ).order_by('-total_bet_amount')
    
    result = []
    for stat in stats_by_user:
        bet_amount = stat['total_bet_amount'] or 0
        win_amount = stat['total_win_amount'] or 0
        result.append({
            'user_id': stat['user__id'],
            'username': stat['user__username'],
            'total_bets': stat['total_bets'],
            'total_bet_amount': str(bet_amount),
            'total_win_amount': str(win_amount),
            'profit_loss': str(bet_amount - win_amount),
        })
    
    # Total summary
    total = bets.aggregate(
        total_bets=Count('id'),
        total_bet=Sum('bet_amount'),
        total_win=Sum('win_amount')
    )
    
    return Response({
        'by_client': result,
        'summary': {
            'total_bets': total['total_bets'] or 0,
            'total_bet_amount': str(total['total_bet'] or 0),
            'total_win_amount': str(total['total_win'] or 0),
            'profit_loss': str((total['total_bet'] or 0) - (total['total_win'] or 0)),
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def top_winners(request):
    """
    Get top winners list.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    limit = int(request.query_params.get('limit', 10))
    
    bets = Bet.objects.filter(user__in=hierarchy_users, result='WON')
    
    if date_from:
        bets = bets.filter(placed_at__date__gte=date_from)
    if date_to:
        bets = bets.filter(placed_at__date__lte=date_to)
    
    # Group by user and calculate profit
    top_winners = bets.values('user__id', 'user__username').annotate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount')
    ).order_by('-total_win_amount')[:limit]
    
    result = []
    for winner in top_winners:
        bet_amount = winner['total_bet_amount'] or 0
        win_amount = winner['total_win_amount'] or 0
        result.append({
            'user_id': winner['user__id'],
            'username': winner['user__username'],
            'total_bets': winner['total_bets'],
            'total_bet_amount': str(bet_amount),
            'total_win_amount': str(win_amount),
            'profit': str(win_amount - bet_amount),
        })
    
    return Response(result)
