"""
User views for Transactions.
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
def transactions(request):
    """
    Get all transactions for current user.
    """
    user = request.user
    
    transaction_type = request.query_params.get('type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = WalletTransaction.objects.filter(user=user).order_by('-created_at')

    if transaction_type:
        if transaction_type == 'WIN':
            queryset = queryset.filter(type='BET_SETTLED', amount__gt=0)
        elif transaction_type == 'LOSS':
            queryset = queryset.filter(Q(type='BET_PLACED') | Q(type='BET_SETTLED', amount__lt=0))
        else:
            queryset = queryset.filter(type=transaction_type)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Summary by type
    summary = {
        'deposit': queryset.filter(type='DEPOSIT').aggregate(
            count=Sum('id', output_field=None),
            total=Sum('amount')
        ),
        'withdraw': queryset.filter(type='WITHDRAW').aggregate(
            total=Sum('amount')
        ),
        'bonus': queryset.filter(type='BONUS').aggregate(
            total=Sum('amount')
        ),
        'bet_placed': queryset.filter(type='BET_PLACED').aggregate(
            total=Sum('amount')
        ),
        'bet_settled': queryset.filter(type='BET_SETTLED').aggregate(
            total=Sum('amount')
        ),
    }
    
    # Count by type
    type_counts = {
        'deposit': queryset.filter(type='DEPOSIT').count(),
        'withdraw': queryset.filter(type='WITHDRAW').count(),
        'bonus': queryset.filter(type='BONUS').count(),
        'bet_placed': queryset.filter(type='BET_PLACED').count(),
        'bet_settled': queryset.filter(type='BET_SETTLED').count(),
    }
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = WalletTransactionSerializer(page_obj, many=True)
    
    return Response({
        'current_balance': str(user.wallet_balance),
        'summary': {
            'deposit': str(summary['deposit']['total'] or 0),
            'withdraw': str(summary['withdraw']['total'] or 0),
            'bonus': str(summary['bonus']['total'] or 0),
            'bet_placed': str(summary['bet_placed']['total'] or 0),
            'bet_settled': str(summary['bet_settled']['total'] or 0),
        },
        'counts': type_counts,
        'transactions': {
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        }
    })
