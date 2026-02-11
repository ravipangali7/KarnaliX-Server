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

        # PIN confirmation required
        data = request.data
        pin = (data.get('pin') or (request.POST.get('pin', '') if request.POST else '') or '').strip()
        if not user.pin:
            return Response({'error': 'Your account has no PIN set. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
        if pin != user.pin:
            return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)

        # Support both JSON and multipart/form-data (for screenshot upload)
        if hasattr(request, 'FILES') and request.FILES:
            # Form data: fields may be in request.POST or request.data
            payment_mode_id = data.get('payment_mode_id') or (request.POST.get('payment_mode_id') if request.POST else None)
            remarks = data.get('remarks') or (request.POST.get('remarks', '') if request.POST else '')
        else:
            payment_mode_id = data.get('payment_mode_id')
            remarks = data.get('remarks', '')

        amount = Decimal(str(data.get('amount') or (request.POST.get('amount', 0) if request.POST else 0)))
        screenshot_file = request.FILES.get('screenshot') if hasattr(request, 'FILES') else None

        if amount <= 0:
            return Response({'error': 'Amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)

        if not screenshot_file:
            return Response({'error': 'Payment screenshot is required. Please upload proof of payment.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type (image or PDF)
        allowed_types = ('image/jpeg', 'image/png', 'image/jpg', 'image/webp', 'application/pdf')
        if screenshot_file.content_type not in allowed_types:
            return Response({'error': 'Screenshot must be PNG, JPG, WEBP, or PDF (max 5MB).'}, status=status.HTTP_400_BAD_REQUEST)
        if screenshot_file.size > 5 * 1024 * 1024:
            return Response({'error': 'Screenshot size must be less than 5MB.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate payment mode: only accept numeric id from parent-configured PaymentMode
        payment_mode = None
        if payment_mode_id is not None and payment_mode_id != '':
            try:
                payment_mode_id_int = int(payment_mode_id)
            except (TypeError, ValueError):
                return Response({
                    'error': 'Invalid payment mode. No payment methods are configured for your account; please contact your referrer.'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                payment_mode = PaymentMode.objects.get(id=payment_mode_id_int, status='ACTIVE')
            except PaymentMode.DoesNotExist:
                return Response({'error': 'Invalid payment mode'}, status=status.HTTP_400_BAD_REQUEST)

        # Create deposit request with screenshot
        deposit_request = ClientRequest.objects.create(
            user=user,
            request_type='DEPOSIT',
            amount=amount,
            payment_mode=payment_mode,
            remarks=remarks or '',
            screenshot=screenshot_file
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
    - If logged-in user is MASTER/SUPER/POWERHOUSE: include their own payment modes (so they can deposit).
    - If logged-in user is USER (client): use parent then grandparent; fallback to referred_by if no parent.
    """
    user = request.user

    # One-time sync: set parent from referred_by when missing (so client sees master's payment methods)
    if (
        user.role == 'USER'
        and user.parent is None
        and getattr(user, 'referred_by_id', None)
        and user.referred_by_id
    ):
        ref = user.referred_by
        if ref and ref.role in ('POWERHOUSE', 'SUPER', 'MASTER'):
            user.parent = ref
            user.save(update_fields=['parent'])

    payment_modes = []
    source_users = []

    # Hierarchy users (Master/Super/Powerhouse) see their own payment modes when depositing
    if user.role in ('POWERHOUSE', 'SUPER', 'MASTER'):
        source_users.append(user)
    # Client users see their parent's (and grandparent's) payment modes
    if user.parent:
        if user.parent not in source_users:
            source_users.append(user.parent)
        if user.parent.parent and user.parent.parent not in source_users:
            source_users.append(user.parent.parent)
    elif getattr(user, 'referred_by_id', None) and user.referred_by_id:
        ref = user.referred_by
        if ref and ref.role in ('POWERHOUSE', 'SUPER', 'MASTER'):
            if ref not in source_users:
                source_users.append(ref)
            if ref.parent and ref.parent not in source_users:
                source_users.append(ref.parent)

    seen_ids = set()
    for source in source_users:
        for pm in PaymentMode.objects.filter(user=source, status='ACTIVE'):
            if pm.id not in seen_ids:
                seen_ids.add(pm.id)
                payment_modes.append(pm)

    serializer = PaymentModeSerializer(payment_modes, many=True, context={'request': request})
    return Response(serializer.data)
