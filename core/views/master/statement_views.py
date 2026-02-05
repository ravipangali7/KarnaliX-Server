"""
Master views for Account and Bonus statements.
"""
from django.db.models import Sum, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import User, WalletTransaction, Bonus
from core.serializers.financial_serializers import WalletTransactionSerializer, BonusSerializer
from core.permissions import master_required


def get_hierarchy_users(user):
    """Get users under this Master."""
    if user.role in ['POWERHOUSE', 'SUPER']:
        return User.objects.all()
    else:
        return User.objects.filter(Q(id=user.id) | Q(parent=user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def account_statement(request):
    """
    Get account statement for users under this Master.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    user_id = request.query_params.get('user_id')
    transaction_type = request.query_params.get('type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = WalletTransaction.objects.filter(user__in=hierarchy_users).order_by('-created_at')
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def bonus_statement(request):
    """
    Get bonus statement for users under this Master.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    user_id = request.query_params.get('user_id')
    bonus_type = request.query_params.get('type')
    status_filter = request.query_params.get('status')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = Bonus.objects.filter(user__in=hierarchy_users).order_by('-created_at')
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if bonus_type:
        queryset = queryset.filter(bonus_type=bonus_type)
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Summary
    summary = queryset.aggregate(
        total_bonus=Sum('amount'),
        total_active=Sum('amount', filter=Q(status='ACTIVE')),
        total_completed=Sum('amount', filter=Q(status='COMPLETED')),
    )
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = BonusSerializer(page_obj, many=True)
    
    return Response({
        'summary': {
            'total_bonus': str(summary['total_bonus'] or 0),
            'total_active': str(summary['total_active'] or 0),
            'total_completed': str(summary['total_completed'] or 0),
        },
        'bonuses': {
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        }
    })
