"""
Powerhouse views for listing all bets.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import Bet
from core.serializers.game_serializers import BetSerializer
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def bet_list(request):
    """
    List all bets (powerhouse). Pagination and optional filters: user_id, result, date.
    """
    queryset = Bet.objects.select_related('user', 'game', 'game__provider').order_by('-placed_at')
    user_id = request.query_params.get('user_id')
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    result = request.query_params.get('result')
    if result:
        queryset = queryset.filter(result=result.upper())
    date = request.query_params.get('date')
    if date:
        queryset = queryset.filter(placed_at__date=date)
    page = request.query_params.get('page', 1)
    page_size = min(int(request.query_params.get('page_size', 20) or 20), 100)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    serializer = BetSerializer(page_obj, many=True)
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })
