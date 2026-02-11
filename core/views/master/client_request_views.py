"""
Master views for Client Requests (Deposit/Withdraw).
"""
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User, ClientRequest, WalletTransaction
from core.serializers.financial_serializers import ClientRequestSerializer
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
def deposit_list(request):
    """Get all deposit requests for users under this Master."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    queryset = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='DEPOSIT'
    ).order_by('-created_at')
    
    # Filters
    status_filter = request.query_params.get('status')
    user_id = request.query_params.get('user_id')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Summary
    summary = {
        'total': queryset.aggregate(total=Sum('amount'))['total'] or 0,
        'pending': queryset.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0,
        'approved': queryset.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_count': queryset.filter(status='PENDING').count(),
    }
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = ClientRequestSerializer(page_obj, many=True)
    
    return Response({
        'summary': summary,
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def withdraw_list(request):
    """Get all withdraw requests for users under this Master."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    queryset = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='WITHDRAW'
    ).order_by('-created_at')
    
    # Filters
    status_filter = request.query_params.get('status')
    user_id = request.query_params.get('user_id')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Summary
    summary = {
        'total': queryset.aggregate(total=Sum('amount'))['total'] or 0,
        'pending': queryset.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0,
        'approved': queryset.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_count': queryset.filter(status='PENDING').count(),
    }
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = ClientRequestSerializer(page_obj, many=True)
    
    return Response({
        'summary': summary,
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def total_dw(request):
    """Get total deposit/withdraw summary."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    deposit_qs = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='DEPOSIT', status='APPROVED'
    )
    withdraw_qs = ClientRequest.objects.filter(
        user__in=hierarchy_users, request_type='WITHDRAW', status='APPROVED'
    )
    
    if date_from:
        deposit_qs = deposit_qs.filter(created_at__date__gte=date_from)
        withdraw_qs = withdraw_qs.filter(created_at__date__gte=date_from)
    if date_to:
        deposit_qs = deposit_qs.filter(created_at__date__lte=date_to)
        withdraw_qs = withdraw_qs.filter(created_at__date__lte=date_to)
    
    total_deposit = deposit_qs.aggregate(total=Sum('amount'))['total'] or 0
    total_withdraw = withdraw_qs.aggregate(total=Sum('amount'))['total'] or 0
    
    return Response({
        'total_deposit': str(total_deposit),
        'total_withdraw': str(total_withdraw),
        'net': str(total_deposit - total_withdraw),
        'deposit_count': deposit_qs.count(),
        'withdraw_count': withdraw_qs.count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@master_required
def approve_request(request, request_id):
    """Approve a client request."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        client_request = ClientRequest.objects.get(id=request_id, user__in=hierarchy_users)
    except ClientRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if client_request.status != 'PENDING':
        return Response({'error': 'Request is not pending'}, status=status.HTTP_400_BAD_REQUEST)

    pin = request.data.get('pin', '').strip()
    if not user.pin:
        return Response({'error': 'Your account has no PIN set. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    if pin != user.pin:
        return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)
    
    target_user = client_request.user
    balance_before = target_user.wallet_balance
    
    if client_request.request_type == 'DEPOSIT':
        target_user.wallet_balance += client_request.amount
        transaction_type = 'DEPOSIT'
    else:
        if target_user.wallet_balance < client_request.amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        target_user.wallet_balance -= client_request.amount
        transaction_type = 'WITHDRAW'
    
    target_user.save()
    
    client_request.status = 'APPROVED'
    client_request.processed_by = user
    client_request.processed_at = timezone.now()
    client_request.remarks = request.data.get('remarks', '')
    client_request.save()
    
    WalletTransaction.objects.create(
        user=target_user,
        type=transaction_type,
        amount=client_request.amount,
        balance_before=balance_before,
        balance_after=target_user.wallet_balance,
        reference_id=str(client_request.id),
        remarks=f'{transaction_type} request approved',
        created_by=user
    )
    
    return Response(ClientRequestSerializer(client_request).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@master_required
def reject_request(request, request_id):
    """Reject a client request."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        client_request = ClientRequest.objects.get(id=request_id, user__in=hierarchy_users)
    except ClientRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if client_request.status != 'PENDING':
        return Response({'error': 'Request is not pending'}, status=status.HTTP_400_BAD_REQUEST)
    
    client_request.status = 'REJECTED'
    client_request.processed_by = user
    client_request.processed_at = timezone.now()
    client_request.remarks = request.data.get('remarks', 'Rejected')
    client_request.save()
    
    return Response(ClientRequestSerializer(client_request).data)
