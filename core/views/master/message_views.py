from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Message, User, UserRole
from core.serializers import MessageSerializer, MessageCreateSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    partner_id = request.query_params.get('partner_id')
    qs = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver')
    if partner_id:
        try:
            pid = int(partner_id)
            qs = qs.filter(Q(sender_id=pid) | Q(receiver_id=pid))
        except (TypeError, ValueError):
            pass
    qs = qs.order_by('created_at')[:200]
    return Response(MessageSerializer(qs, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_create(request):
    err = require_role(request, [UserRole.MASTER])
    if err:
        return err
    receiver_id = request.data.get('receiver')
    receiver = User.objects.filter(pk=receiver_id).first()
    if not receiver:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.PLAYER and receiver.parent_id != request.user.id:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.SUPER and receiver.id != request.user.parent_id:
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    ser = MessageCreateSerializer(data={**request.data, 'receiver': receiver_id})
    ser.is_valid(raise_exception=True)
    msg = ser.save(sender=request.user)
    return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
