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
    err = require_role(request, [UserRole.SUPER])
    if err: return err
    partner_id = request.query_params.get('partner_id')
    qs = Message.objects.filter(sender=request.user) | Message.objects.filter(receiver=request.user)
    if partner_id: qs = qs.filter(sender_id=partner_id) | qs.filter(receiver_id=partner_id)
    qs = qs.select_related('sender', 'receiver').order_by('created_at')[:200]
    return Response(MessageSerializer(qs.distinct(), many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_create(request):
    err = require_role(request, [UserRole.SUPER])
    if err: return err
    receiver_id = request.data.get('receiver')
    receiver = User.objects.filter(pk=receiver_id).first()
    if not receiver: return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.MASTER and receiver.parent_id != request.user.id: return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    if receiver.role == UserRole.POWERHOUSE and receiver.id != request.user.parent_id: return Response({'detail': 'Invalid receiver.'}, status=status.HTTP_400_BAD_REQUEST)
    ser = MessageCreateSerializer(data={**request.data, 'receiver': receiver_id})
    ser.is_valid(raise_exception=True)
    msg = ser.save(sender=request.user)
    return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
