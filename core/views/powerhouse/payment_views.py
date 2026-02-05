"""
Powerhouse views for Payment Mode management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import PaymentMode
from core.serializers.financial_serializers import PaymentModeSerializer, PaymentModeCreateSerializer
from core.permissions import powerhouse_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def payment_mode_list_create(request):
    """
    GET: List current user's payment modes
    POST: Create a new payment mode
    """
    user = request.user

    if request.method == 'GET':
        queryset = PaymentMode.objects.filter(user=user).order_by('-created_at')

        payment_type = request.query_params.get('type')
        status_filter = request.query_params.get('status')

        if payment_type:
            queryset = queryset.filter(type=payment_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = PaymentModeSerializer(queryset, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PaymentModeCreateSerializer(data=request.data)
        if serializer.is_valid():
            payment_mode = serializer.save(user=user)
            return Response(PaymentModeSerializer(payment_mode).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def payment_mode_detail(request, payment_id):
    """
    GET: Get payment mode details
    PATCH: Update payment mode
    DELETE: Deactivate payment mode
    """
    user = request.user

    try:
        payment_mode = PaymentMode.objects.get(id=payment_id, user=user)
    except PaymentMode.DoesNotExist:
        return Response({'error': 'Payment mode not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PaymentModeSerializer(payment_mode)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        serializer = PaymentModeCreateSerializer(payment_mode, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PaymentModeSerializer(payment_mode).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        payment_mode.status = 'INACTIVE'
        payment_mode.save()
        return Response({'message': 'Payment mode deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def payment_mode_toggle(request, payment_id):
    """
    Toggle payment mode status (ACTIVE/INACTIVE).
    """
    user = request.user

    try:
        payment_mode = PaymentMode.objects.get(id=payment_id, user=user)
    except PaymentMode.DoesNotExist:
        return Response({'error': 'Payment mode not found'}, status=status.HTTP_404_NOT_FOUND)

    payment_mode.status = 'INACTIVE' if payment_mode.status == 'ACTIVE' else 'ACTIVE'
    payment_mode.save()

    return Response({
        'message': f'Payment mode {"deactivated" if payment_mode.status == "INACTIVE" else "activated"}',
        'status': payment_mode.status
    })
