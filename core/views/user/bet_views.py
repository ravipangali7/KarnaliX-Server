"""
User views for My Bets.
"""
from django.db.models import Sum, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import Bet
from core.serializers.game_serializers import BetSerializer
from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def my_bets(request):
    """
    Get all bets for current user.
    """
    user = request.user
    
    result_filter = request.query_params.get('result')
    game_type = request.query_params.get('game_type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = Bet.objects.filter(user=user).order_by('-placed_at')
    
    if result_filter:
        queryset = queryset.filter(result=result_filter)
    if game_type:
        queryset = queryset.filter(game__game_type=game_type)
    if date_from:
        queryset = queryset.filter(placed_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(placed_at__date__lte=date_to)
    
    # Summary
    summary = queryset.aggregate(
        total_bets=Count('id'),
        total_bet_amount=Sum('bet_amount'),
        total_win_amount=Sum('win_amount'),
    )
    
    pending_count = queryset.filter(result='PENDING').count()
    won_count = queryset.filter(result='WON').count()
    lost_count = queryset.filter(result='LOST').count()
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = BetSerializer(page_obj, many=True)
    
    return Response({
        'summary': {
            'total_bets': summary['total_bets'] or 0,
            'total_bet_amount': str(summary['total_bet_amount'] or 0),
            'total_win_amount': str(summary['total_win_amount'] or 0),
            'pending': pending_count,
            'won': won_count,
            'lost': lost_count,
        },
        'bets': {
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def bet_detail(request, bet_id):
    """
    Get bet details.
    """
    user = request.user
    
    try:
        bet = Bet.objects.get(id=bet_id, user=user)
    except Bet.DoesNotExist:
        return Response({'error': 'Bet not found'}, status=404)
    
    serializer = BetSerializer(bet)
    return Response(serializer.data)
