"""
User views for Results.
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
def results(request):
    """
    Get settled bet results for current user.
    """
    user = request.user
    
    result_filter = request.query_params.get('result')  # WON, LOST, VOID
    game_type = request.query_params.get('game_type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    # Only settled bets (not PENDING)
    queryset = Bet.objects.filter(user=user).exclude(result='PENDING').order_by('-settled_at')
    
    if result_filter:
        queryset = queryset.filter(result=result_filter)
    if game_type:
        queryset = queryset.filter(game__game_type=game_type)
    if date_from:
        queryset = queryset.filter(settled_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(settled_at__date__lte=date_to)
    
    # Summary
    won_stats = queryset.filter(result='WON').aggregate(
        count=Count('id'),
        bet_amount=Sum('bet_amount'),
        win_amount=Sum('win_amount')
    )
    
    lost_stats = queryset.filter(result='LOST').aggregate(
        count=Count('id'),
        bet_amount=Sum('bet_amount')
    )
    
    void_count = queryset.filter(result='VOID').count()
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = BetSerializer(page_obj, many=True)
    
    return Response({
        'summary': {
            'won': {
                'count': won_stats['count'] or 0,
                'bet_amount': str(won_stats['bet_amount'] or 0),
                'win_amount': str(won_stats['win_amount'] or 0),
            },
            'lost': {
                'count': lost_stats['count'] or 0,
                'bet_amount': str(lost_stats['bet_amount'] or 0),
            },
            'void': void_count,
            'total': queryset.count(),
        },
        'results': {
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        }
    })
