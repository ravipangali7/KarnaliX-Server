"""Powerhouse: Super, Master, Player CRUD."""
import secrets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role, get_supers_queryset, get_masters_queryset, get_players_queryset
from core.models import User, UserRole
from core.serializers import UserListSerializer, UserDetailSerializer, UserCreateUpdateSerializer


def _get_queryset(request, role_type):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err, None
    if role_type == 'super':
        qs = get_supers_queryset(request.user)
    elif role_type == 'master':
        qs = get_masters_queryset(request.user)
    else:
        qs = get_players_queryset(request.user)
    return None, qs


def _user_list_response(request, role_type):
    """Shared list logic; request is DRF Request. Returns Response."""
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    serializer = UserListSerializer(qs.order_by('-created_at'), many=True)
    return Response(serializer.data)


def _user_detail_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(UserDetailSerializer(obj).data)


def _user_create_response(request, role_type):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    role_map = {'super': UserRole.SUPER, 'master': UserRole.MASTER, 'player': UserRole.PLAYER}
    data = request.data.copy()
    data['role'] = role_map[role_type]
    if role_type == 'super':
        data['parent'] = request.user.id
    elif role_type == 'master':
        data['parent'] = data.get('parent')
    elif role_type == 'player':
        data['parent'] = data.get('parent')
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


def _user_update_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    ser = UserCreateUpdateSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(UserDetailSerializer(obj).data)


def _user_delete_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _verify_admin_pin(request):
    """Verify admin PIN from request.data. Returns None or error Response."""
    pin = request.data.get('pin')
    if not pin:
        return Response({'detail': 'PIN required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _user_regenerate_pin_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    pin_err = _verify_admin_pin(request)
    if pin_err:
        return pin_err
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    new_pin = ''.join(secrets.choice('0123456789') for _ in range(6))
    obj.pin = new_pin
    obj.save(update_fields=['pin'])
    return Response({'detail': 'PIN regenerated successfully.'})


def _user_reset_password_response(request, role_type, pk):
    err, qs = _get_queryset(request, role_type)
    if err:
        return err
    pin_err = _verify_admin_pin(request)
    if pin_err:
        return pin_err
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'new_password required.'}, status=status.HTTP_400_BAD_REQUEST)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.set_password(new_password)
    obj.save(update_fields=['password'])
    return Response({'detail': 'Password reset successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request, role_type):
    return _user_list_response(request, role_type)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, role_type, pk):
    return _user_detail_response(request, role_type, pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create(request, role_type):
    return _user_create_response(request, role_type)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update(request, role_type, pk):
    return _user_update_response(request, role_type, pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, role_type, pk):
    return _user_delete_response(request, role_type, pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_supers(request):
    return _user_list_response(request, 'super')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_masters(request):
    return _user_list_response(request, 'master')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_players(request):
    return _user_list_response(request, 'player')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_supers(request, pk):
    return _user_detail_response(request, 'super', pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_masters(request, pk):
    return _user_detail_response(request, 'master', pk)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_players(request, pk):
    return _user_detail_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_super(request):
    return _user_create_response(request, 'super')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_master(request):
    return _user_create_response(request, 'master')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_player(request):
    return _user_create_response(request, 'player')


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_super(request, pk):
    return _user_update_response(request, 'super', pk)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_master(request, pk):
    return _user_update_response(request, 'master', pk)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_player(request, pk):
    return _user_update_response(request, 'player', pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_super(request, pk):
    return _user_delete_response(request, 'super', pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_master(request, pk):
    return _user_delete_response(request, 'master', pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_player(request, pk):
    return _user_delete_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_super(request, pk):
    return _user_regenerate_pin_response(request, 'super', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_master(request, pk):
    return _user_regenerate_pin_response(request, 'master', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_regenerate_pin_player(request, pk):
    return _user_regenerate_pin_response(request, 'player', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_super(request, pk):
    return _user_reset_password_response(request, 'super', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_master(request, pk):
    return _user_reset_password_response(request, 'master', pk)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password_player(request, pk):
    return _user_reset_password_response(request, 'player', pk)
