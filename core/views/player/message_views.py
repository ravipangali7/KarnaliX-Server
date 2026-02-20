from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.permissions import require_role
from core.models import Message, UserRole
from core.serializers import MessageSerializer, MessageCreateSerializer
from core.channel_utils import broadcast_new_message_to_receiver

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    partner_id = request.query_params.get('partner_id')
    qs = Message.objects.filter(sender=request.user) | Message.objects.filter(receiver=request.user)
    if partner_id:
        try:
            pid = int(partner_id)
            qs = qs.filter(sender_id=pid) | qs.filter(receiver_id=pid)
        except (TypeError, ValueError):
            pass
    qs = qs.select_related('sender', 'receiver').order_by('created_at').distinct()[:200]
    return Response(MessageSerializer(qs, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_create(request):
    err = require_role(request, [UserRole.PLAYER])
    if err: return err
    try:
        receiver_id = int(request.data.get('receiver'))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver_id != request.user.parent_id: return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    data = {**request.data, 'receiver': receiver_id}
    if request.FILES:
        if 'file' in request.FILES:
            data['file'] = request.FILES['file']
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']
    ser = MessageCreateSerializer(data=data)
    ser.is_valid(raise_exception=True)
    msg = ser.save(sender=request.user)
    data = MessageSerializer(msg).data
    broadcast_new_message_to_receiver(msg.receiver_id, data)
    broadcast_new_message_to_receiver(msg.sender_id, data)
    return Response(data, status=status.HTTP_201_CREATED)
