from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import UserRole, Deposit, Withdraw, Transaction, GameLog, PaymentMode
from core.serializers import DepositSerializer, WithdrawSerializer, TransactionSerializer, GameLogSerializer, PaymentModeSerializer


def _get_related_transaction(game_log):
    """Return the transaction linked to this game log (by FK or by user + remarks)."""
    if hasattr(game_log, 'transactions') and game_log.transactions.exists():
        return game_log.transactions.first()
    return Transaction.objects.filter(
        user=game_log.user,
        remarks=f"Game round {game_log.round}",
    ).first()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    u = request.user
    ctx = {'request': request}
    return Response({
        'main_balance': str(u.main_balance or 0),
        'bonus_balance': str(u.bonus_balance or 0),
        'deposits': DepositSerializer(Deposit.objects.filter(user=u).select_related('payment_mode').order_by('-created_at')[:50], many=True, context=ctx).data,
        'withdrawals': WithdrawSerializer(Withdraw.objects.filter(user=u).select_related('payment_mode').order_by('-created_at')[:50], many=True, context=ctx).data,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    return Response(TransactionSerializer(Transaction.objects.filter(user=request.user).order_by('-created_at')[:200], many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_list(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    return Response(GameLogSerializer(GameLog.objects.filter(user=request.user).select_related('game', 'provider').order_by('-created_at')[:200], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_detail(request, pk):
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    log = GameLog.objects.filter(user=request.user, pk=pk).select_related('game', 'provider', 'user').first()
    if not log:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    tx = _get_related_transaction(log)
    return Response({
        'game_log': GameLogSerializer(log).data,
        'transaction': TransactionSerializer(tx).data if tx else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deposit_payment_modes(request):
    """Return master's (parent's) payment modes for deposit. Player selects one when requesting deposit."""
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    parent = request.user.parent
    if not parent:
        return Response([])
    qs = PaymentMode.objects.filter(user=parent, status='approved')
    return Response(PaymentModeSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payment_mode_list_create(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    if request.method == 'GET':
        return Response(PaymentModeSerializer(PaymentMode.objects.filter(user=request.user), many=True, context={'request': request}).data)
    data = request.data.copy()
    if request.FILES:
        for key in request.FILES:
            data[key] = request.FILES[key]
    data['user'] = request.user.id
    ser = PaymentModeSerializer(data=data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def payment_mode_detail(request, pk):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    obj = PaymentMode.objects.filter(pk=pk, user=request.user).first()
    if not obj: return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET': return Response(PaymentModeSerializer(obj, context={'request': request}).data)
    if request.method == 'DELETE': obj.delete(); return Response(status=status.HTTP_204_NO_CONTENT)
    ser = PaymentModeSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data)
