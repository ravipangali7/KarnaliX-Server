from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from core.permissions import require_role, get_masters_queryset, get_players_queryset
from core.models import Deposit, PaymentMode, User, UserRole
from core.serializers import DepositSerializer, DepositCreateSerializer, PaymentModeSerializer
from core.services.deposit_service import approve_deposit


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_payment_modes(request):
    """Return payment modes for deposit target (user_id). For player target returns parent's modes."""
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'detail': 'user_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid user_id.'}, status=status.HTTP_400_BAD_REQUEST)
    masters_qs = get_masters_queryset(request.user).filter(pk=user_id)
    players_qs = get_players_queryset(request.user).filter(pk=user_id)
    if not masters_qs.exists() and not players_qs.exists():
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)
    target = User.objects.filter(pk=user_id).first()
    owner_id = target.parent_id if target and target.role == UserRole.PLAYER else user_id
    qs = PaymentMode.objects.filter(user_id=owner_id, is_active=True)
    return Response(PaymentModeSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_list(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = Deposit.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user)
    ).select_related('user', 'payment_mode').order_by('-created_at')[:500]
    return Response(DepositSerializer(qs, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_detail(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    obj = Deposit.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user), pk=pk
    ).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(DepositSerializer(obj).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_create(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    ser = DepositCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    dep = Deposit.objects.create(user_id=request.data.get('user_id'), **ser.validated_data)
    return Response(DepositSerializer(dep).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_direct(request):
    """Verify PIN first; only then create and approve deposit. No deposit created if PIN is invalid."""
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.data.get('user_id')
    amount_raw = request.data.get('amount')
    remarks = request.data.get('remarks', '') or ''
    if user_id is None:
        return Response({'detail': 'user_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount_raw is None:
        return Response({'detail': 'amount required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount_raw))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    masters_qs = get_masters_queryset(request.user).filter(pk=user_id)
    players_qs = get_players_queryset(request.user).filter(pk=user_id)
    if not masters_qs.exists() and not players_qs.exists():
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)

    target = User.objects.filter(pk=user_id).first()
    owner_id = target.parent_id if target and target.role == UserRole.PLAYER else user_id
    payment_mode_id = request.data.get('payment_mode')
    payment_mode = None
    if payment_mode_id is not None:
        payment_mode = PaymentMode.objects.filter(pk=payment_mode_id, user_id=owner_id).first()
        if not payment_mode:
            return Response({'detail': 'Invalid payment mode.'}, status=status.HTTP_400_BAD_REQUEST)

    dep = Deposit.objects.create(
        user_id=user_id, amount=amount, remarks=remarks, status='pending',
        payment_mode_id=payment_mode.pk if payment_mode else None
    )
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        dep.delete()
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_approve(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin = request.data.get('pin')
    if not pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    dep = Deposit.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user),
        pk=pk, status='pending'
    ).first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    ok, msg = approve_deposit(dep, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(DepositSerializer(dep).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_reject(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    dep = Deposit.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user),
        pk=pk, status='pending'
    ).first()
    if not dep:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    dep.status = 'rejected'
    dep.reject_reason = request.data.get('reject_reason', '')
    dep.processed_by = request.user
    dep.processed_at = timezone.now()
    dep.save()
    return Response(DepositSerializer(dep).data)
