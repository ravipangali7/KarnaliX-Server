from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role, get_players_queryset
from core.models import UserRole
from core.serializers import UserListSerializer, UserDetailSerializer, UserCreateUpdateSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = get_players_queryset(request.user).order_by('-created_at')
    return Response(UserListSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def player_detail(request, pk):
    err = require_role(request, [UserRole.MASTER])
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
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    data = request.data.copy()
    data['role'] = UserRole.PLAYER
    data['parent'] = request.user.id
    ser = UserCreateUpdateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def player_update(request, pk):
    err = require_role(request, [UserRole.MASTER])
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
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    qs = get_players_queryset(request.user)
    obj = qs.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    obj.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
