"""
User views for Account Statement.
"""
from django.db.models import Sum, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import WalletTransaction
from core.serializers.financial_serializers import WalletTransactionSerializer
from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def account_statement(request):
    """
    Get account statement for current user.
    """
    user = request.user
    
    transaction_type = request.query_params.get('type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = WalletTransaction.objects.filter(user=user).order_by('-created_at')
    
    if transaction_type:
        queryset = queryset.filter(type=transaction_type)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Summary
    summary = queryset.aggregate(
        total_deposit=Sum('amount', filter=Q(type='DEPOSIT')),
        total_withdraw=Sum('amount', filter=Q(type='WITHDRAW')),
        total_bonus=Sum('amount', filter=Q(type='BONUS')),
        total_bet=Sum('amount', filter=Q(type='BET_PLACED')),
        total_win=Sum('amount', filter=Q(type='BET_SETTLED')),
    )
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = WalletTransactionSerializer(page_obj, many=True)
    
    return Response({
        'current_balance': str(user.wallet_balance),
        'summary': {
            'total_deposit': str(summary['total_deposit'] or 0),
            'total_withdraw': str(summary['total_withdraw'] or 0),
            'total_bonus': str(summary['total_bonus'] or 0),
            'total_bet': str(summary['total_bet'] or 0),
            'total_win': str(summary['total_win'] or 0),
        },
        'transactions': {
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        }
    })
