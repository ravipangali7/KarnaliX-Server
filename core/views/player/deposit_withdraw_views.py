from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Deposit, Withdraw, PaymentMode, UserRole
from core.serializers import DepositSerializer, DepositCreateSerializer, WithdrawSerializer, WithdrawCreateSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_request(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    ser = DepositCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    dep = Deposit.objects.create(user=request.user, **ser.validated_data)
    return Response(DepositSerializer(dep).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_request(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    parent = request.user.parent
    if not parent:
        return Response({'detail': 'No parent account.'}, status=status.HTTP_400_BAD_REQUEST)
    if not PaymentMode.objects.filter(user=parent, status='approved').exists():
        return Response({'detail': 'At least one payment method must be approved before withdrawal.'}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get('password')
    if not password or not request.user.check_password(password):
        return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    ser = WithdrawCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data.copy()
    payment_mode = data.get('payment_mode')
    if payment_mode:
        if payment_mode.user_id != parent.id or payment_mode.status != 'approved':
            return Response({'detail': 'Selected payment method is invalid or not approved.'}, status=status.HTTP_400_BAD_REQUEST)
    wd = Withdraw.objects.create(user=request.user, **data)
    return Response(WithdrawSerializer(wd).data, status=status.HTTP_201_CREATED)
