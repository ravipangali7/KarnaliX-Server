"""
User views for Withdraw requests.
"""
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import ClientRequest, PaymentMode, UserActivityLog
from core.serializers.financial_serializers import (
    ClientRequestSerializer, PaymentModeSerializer, PaymentModeCreateSerializer
)
from core.permissions import user_required


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@user_required
def withdraw(request):
    """
    GET: Get withdraw history
    POST: Create a withdraw request
    """
    user = request.user
    
    if request.method == 'GET':
        queryset = ClientRequest.objects.filter(
            user=user, request_type='WITHDRAW'
        ).order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Summary
        summary = {
            'total': queryset.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0,
            'pending': queryset.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0,
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
            'available_balance': str(user.wallet_balance - user.exposure_balance),
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    
    elif request.method == 'POST':
        from decimal import Decimal

        pin = (request.data.get('pin') or '').strip()
        if not user.pin:
            return Response({'error': 'Your account has no PIN set. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
        if pin != user.pin:
            return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_mode_id = request.data.get('payment_mode_id')
        remarks = request.data.get('remarks', '')
        
        if amount <= 0:
            return Response({'error': 'Amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check available balance
        available_balance = user.wallet_balance - user.exposure_balance
        if amount > available_balance:
            return Response(
                {'error': f'Insufficient balance. Available: {available_balance}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate payment mode (user's own payment mode)
        payment_mode = None
        if payment_mode_id:
            try:
                payment_mode = PaymentMode.objects.get(id=payment_mode_id, user=user, status='ACTIVE')
            except PaymentMode.DoesNotExist:
                return Response({'error': 'Invalid payment mode'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create withdraw request
        withdraw_request = ClientRequest.objects.create(
            user=user,
            request_type='WITHDRAW',
            amount=amount,
            payment_mode=payment_mode,
            remarks=remarks
        )
        
        # Log activity
        UserActivityLog.objects.create(
            user=user,
            action='WITHDRAW_REQUEST',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        return Response(ClientRequestSerializer(withdraw_request).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@user_required
def my_payment_modes(request):
    """
    GET: Get user's payment modes
    POST: Add a new payment mode
    """
    user = request.user
    
    if request.method == 'GET':
        queryset = PaymentMode.objects.filter(user=user).order_by('-created_at')
        serializer = PaymentModeSerializer(queryset, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = PaymentModeCreateSerializer(data=request.data)
        if serializer.is_valid():
            payment_mode = serializer.save(user=user)
            return Response(PaymentModeSerializer(payment_mode).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@user_required
def delete_payment_mode(request, payment_id):
    """
    Delete/deactivate a payment mode.
    """
    user = request.user
    
    try:
        payment_mode = PaymentMode.objects.get(id=payment_id, user=user)
    except PaymentMode.DoesNotExist:
        return Response({'error': 'Payment mode not found'}, status=status.HTTP_404_NOT_FOUND)
    
    payment_mode.status = 'INACTIVE'
    payment_mode.save()
    
    return Response({'message': 'Payment mode deactivated'})
