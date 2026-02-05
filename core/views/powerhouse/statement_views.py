"""
Powerhouse views for Account and Bonus statements.
"""
from django.db.models import Sum, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from datetime import datetime

from core.models import User, WalletTransaction, Bonus
from core.serializers.financial_serializers import WalletTransactionSerializer, BonusSerializer
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def account_statement(request):
    """
    Get account statement for all users or specific user.
    """
    user_id = request.query_params.get('user_id')
    transaction_type = request.query_params.get('type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = WalletTransaction.objects.all().order_by('-created_at')
    
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
@powerhouse_required
def bonus_statement(request):
    """
    Get bonus statement for all users or specific user.
    """
    user_id = request.query_params.get('user_id')
    bonus_type = request.query_params.get('type')
    status_filter = request.query_params.get('status')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = Bonus.objects.all().order_by('-created_at')
    
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def grant_bonus(request):
    """
    Grant a bonus to a user.
    """
    from decimal import Decimal
    from core.models import WalletTransaction
    
    user_id = request.data.get('user_id')
    bonus_type = request.data.get('bonus_type', 'MANUAL')
    amount = Decimal(str(request.data.get('amount', 0)))
    rollover = Decimal(str(request.data.get('rollover_requirement', 0)))
    
    if not user_id or amount <= 0:
        return Response({'error': 'User ID and positive amount are required'}, status=400)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    # Create bonus
    bonus = Bonus.objects.create(
        user=user,
        bonus_type=bonus_type,
        amount=amount,
        rollover_requirement=rollover,
        granted_by=request.user
    )
    
    # Update user balance
    balance_before = user.wallet_balance
    user.wallet_balance += amount
    user.save()
    
    # Create transaction
    WalletTransaction.objects.create(
        user=user,
        to_user=user,
        type='BONUS',
        amount=amount,
        balance_before=balance_before,
        balance_after=user.wallet_balance,
        reference_id=str(bonus.id),
        remarks=f'{bonus_type} bonus granted',
        created_by=request.user
    )
    
    return Response(BonusSerializer(bonus).data, status=201)
