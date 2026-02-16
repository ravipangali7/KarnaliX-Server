from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Deposit, Withdraw, UserRole
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
    if request.user.kyc_status != 'approved':
        return Response({'detail': 'KYC must be approved to withdraw.'}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get('password')
    if not password or not request.user.check_password(password):
        return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    ser = WithdrawCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    wd = Withdraw.objects.create(user=request.user, **ser.validated_data)
    return Response(WithdrawSerializer(wd).data, status=status.HTTP_201_CREATED)
