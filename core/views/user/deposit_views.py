"""
User views for Deposit requests.
"""
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import ClientRequest, PaymentMode, UserActivityLog
from core.serializers.financial_serializers import (
    ClientRequestSerializer, ClientRequestCreateSerializer, PaymentModeSerializer
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
def deposit(request):
    """
    GET: Get deposit history
    POST: Create a deposit request
    """
    user = request.user
    
    if request.method == 'GET':
        queryset = ClientRequest.objects.filter(
            user=user, request_type='DEPOSIT'
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
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    
    elif request.method == 'POST':
        from decimal import Decimal
        
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_mode_id = request.data.get('payment_mode_id')
        screenshot = request.data.get('screenshot')
        remarks = request.data.get('remarks', '')
        
        if amount <= 0:
            return Response({'error': 'Amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate payment mode
        payment_mode = None
        if payment_mode_id:
            try:
                payment_mode = PaymentMode.objects.get(id=payment_mode_id, status='ACTIVE')
            except PaymentMode.DoesNotExist:
                return Response({'error': 'Invalid payment mode'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create deposit request
        deposit_request = ClientRequest.objects.create(
            user=user,
            request_type='DEPOSIT',
            amount=amount,
            payment_mode=payment_mode,
            remarks=remarks
        )
        
        # Log activity
        UserActivityLog.objects.create(
            user=user,
            action='DEPOSIT_REQUEST',
            ip_address=get_client_ip(request),
            device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        return Response(ClientRequestSerializer(deposit_request).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def available_payment_modes(request):
    """
    Get available payment modes for deposit.
    """
    user = request.user
    
    # Get payment modes from parent hierarchy (Master/Super/Powerhouse)
    payment_modes = []
    
    if user.parent:
        parent_modes = PaymentMode.objects.filter(user=user.parent, status='ACTIVE')
        payment_modes.extend(parent_modes)
        
        # Also check grandparent
        if user.parent.parent:
            grandparent_modes = PaymentMode.objects.filter(user=user.parent.parent, status='ACTIVE')
            payment_modes.extend(grandparent_modes)
    
    serializer = PaymentModeSerializer(payment_modes, many=True)
    return Response(serializer.data)
