import secrets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role, get_masters_queryset, get_players_queryset
from core.models import User, UserRole
from core.serializers import UserListSerializer, UserDetailSerializer, UserCreateUpdateSerializer


def _verify_super_pin(request):
    """Verify super admin PIN from request.data. Returns None or error Response."""
    pin = request.data.get('pin')
    if not pin:
        return Response({'detail': 'PIN required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def master_list(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_masters_queryset(request.user).order_by('-created_at')
    return Response(UserListSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def master_detail(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_masters_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserDetailSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_create(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    data = request.data.copy()
    data['role'] = UserRole.MASTER
    data['parent'] = request.user.id
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def master_update(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_masters_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ser = UserCreateUpdateSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(UserDetailSerializer(obj).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def master_delete(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_masters_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_regenerate_pin(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin_err = _verify_super_pin(request)
    if pin_err:
        return pin_err
    qs = get_masters_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    new_pin = ''.join(secrets.choice('0123456789') for _ in range(6))
    obj.pin = new_pin
    obj.save(update_fields=['pin'])
    return Response({'detail': 'PIN regenerated successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_reset_password(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin_err = _verify_super_pin(request)
    if pin_err:
        return pin_err
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'new_password required.'}, status=status.HTTP_400_BAD_REQUEST)
    qs = get_masters_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.set_password(new_password)
    obj.save(update_fields=['password'])
    return Response({'detail': 'Password reset successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_list(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_players_queryset(request.user).order_by('-created_at')
    return Response(UserListSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_detail(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserDetailSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def player_create(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    data = request.data.copy()
    data['role'] = UserRole.PLAYER
    data['parent'] = data.get('parent')
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def player_update(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ser = UserCreateUpdateSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(UserDetailSerializer(obj).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def player_delete(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def player_regenerate_pin(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin_err = _verify_super_pin(request)
    if pin_err:
        return pin_err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    new_pin = ''.join(secrets.choice('0123456789') for _ in range(6))
    obj.pin = new_pin
    obj.save(update_fields=['pin'])
    return Response({'detail': 'PIN regenerated successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def player_reset_password(request, pk):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    pin_err = _verify_super_pin(request)
    if pin_err:
        return pin_err
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'new_password required.'}, status=status.HTTP_400_BAD_REQUEST)
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.set_password(new_password)
    obj.save(update_fields=['password'])
    return Response({'detail': 'Password reset successfully.'})
