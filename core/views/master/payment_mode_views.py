"""Master: CRUD for own payment modes."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import PaymentMode, UserRole
from core.serializers import PaymentModeSerializer


def _qs(request):
    return PaymentMode.objects.filter(user=request.user)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payment_mode_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    if request.method == 'GET':
        return Response(PaymentModeSerializer(_qs(request), many=True, context={'request': request}).data)
    data = request.data.copy()
    data['user'] = request.user.id
    ser = PaymentModeSerializer(data=data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_mode_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    obj = _qs(request).filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(PaymentModeSerializer(obj, context={'request': request}).data)


@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def payment_mode_update(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    obj = _qs(request).filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ser = PaymentModeSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(PaymentModeSerializer(ser.instance, context={'request': request}).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def payment_mode_delete(request, pk):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    obj = _qs(request).filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
