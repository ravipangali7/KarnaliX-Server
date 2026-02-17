from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import UserRole
from core.serializers import UserDetailSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_get(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    return Response(UserDetailSerializer(request.user).data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    u = request.user
    for f in ['name', 'phone', 'email', 'whatsapp_number']:
        if f in request.data:
            setattr(u, f, request.data[f])
    u.save()
    return Response(UserDetailSerializer(u).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    old = request.data.get('old_password')
    new = request.data.get('new_password')
    if not old or not new:
        return Response({'detail': 'Required.'}, status=400)
    if not request.user.check_password(old):
        return Response({'detail': 'Invalid password.'}, status=400)
    request.user.set_password(new)
    request.user.save()
    return Response({'detail': 'OK'})
