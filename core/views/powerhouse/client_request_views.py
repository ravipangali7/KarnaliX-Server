"""
Powerhouse views for Client Requests (Deposit/Withdraw).
"""
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from decimal import Decimal

from core.models import User, ClientRequest, WalletTransaction
from core.serializers.financial_serializers import ClientRequestSerializer
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def deposit_list(request):
    """
    Get all deposit requests.
    """
    queryset = ClientRequest.objects.filter(request_type='DEPOSIT').order_by('-created_at')
    
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
@powerhouse_required
def withdraw_list(request):
    """
    Get all withdraw requests.
    """
    queryset = ClientRequest.objects.filter(request_type='WITHDRAW').order_by('-created_at')
    
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
@powerhouse_required
def total_dw(request):
    """
    Get total deposit/withdraw summary.
    """
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    deposit_qs = ClientRequest.objects.filter(request_type='DEPOSIT', status='APPROVED')
    withdraw_qs = ClientRequest.objects.filter(request_type='WITHDRAW', status='APPROVED')
    
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def super_master_dw(request):
    """
    Get deposit/withdraw by Super and Master hierarchy.
    """
    supers = User.objects.filter(role='SUPER')
    
    data = []
    for super_user in supers:
        # Get all users under this super (masters + users under those masters)
        super_children = User.objects.filter(
            Q(parent=super_user) | Q(parent__parent=super_user)
        )
        
        deposits = ClientRequest.objects.filter(
            user__in=super_children, request_type='DEPOSIT', status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        withdrawals = ClientRequest.objects.filter(
            user__in=super_children, request_type='WITHDRAW', status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        data.append({
            'super_id': super_user.id,
            'super_username': super_user.username,
            'total_deposit': str(deposits),
            'total_withdraw': str(withdrawals),
            'net': str(deposits - withdrawals),
            'children_count': super_children.count(),
        })
    
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def approve_request(request, request_id):
    """
    Approve a client request (deposit/withdraw).
    """
    try:
        client_request = ClientRequest.objects.get(id=request_id)
    except ClientRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if client_request.status != 'PENDING':
        return Response({'error': 'Request is not pending'}, status=status.HTTP_400_BAD_REQUEST)

    pin = request.data.get('pin', '').strip()
    if not request.user.pin:
        return Response({'error': 'Your account has no PIN set. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    if pin != request.user.pin:
        return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = client_request.user
    balance_before = user.wallet_balance
    
    if client_request.request_type == 'DEPOSIT':
        user.wallet_balance += client_request.amount
        transaction_type = 'DEPOSIT'
    else:  # WITHDRAW
        if user.wallet_balance < client_request.amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        user.wallet_balance -= client_request.amount
        transaction_type = 'WITHDRAW'
    
    user.save()
    
    # Update request
    client_request.status = 'APPROVED'
    client_request.processed_by = request.user
    client_request.processed_at = timezone.now()
    client_request.remarks = request.data.get('remarks', '')
    client_request.save()
    
    # Create transaction
    WalletTransaction.objects.create(
        user=user,
        type=transaction_type,
        amount=client_request.amount,
        balance_before=balance_before,
        balance_after=user.wallet_balance,
        reference_id=str(client_request.id),
        remarks=f'{transaction_type} request approved',
        created_by=request.user
    )
    
    return Response(ClientRequestSerializer(client_request).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def reject_request(request, request_id):
    """
    Reject a client request.
    """
    try:
        client_request = ClientRequest.objects.get(id=request_id)
    except ClientRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if client_request.status != 'PENDING':
        return Response({'error': 'Request is not pending'}, status=status.HTTP_400_BAD_REQUEST)
    
    client_request.status = 'REJECTED'
    client_request.processed_by = request.user
    client_request.processed_at = timezone.now()
    client_request.remarks = request.data.get('remarks', 'Rejected by admin')
    client_request.save()
    
    return Response(ClientRequestSerializer(client_request).data)
