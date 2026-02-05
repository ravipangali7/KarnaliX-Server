"""
User support tickets - list, create, detail, reply.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import SupportTicket, SupportMessage
from core.serializers.support_serializers import (
    SupportTicketSerializer,
    SupportTicketListSerializer,
    SupportTicketCreateSerializer,
)
from core.permissions import user_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@user_required
def ticket_list_or_create(request):
    """GET: List current user's support tickets. POST: Create a new ticket."""
    if request.method == 'GET':
        queryset = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        serializer = SupportTicketListSerializer(page_obj, many=True)
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    # POST - create
    data = request.data.copy()
    initial_msg = data.get('message') or data.get('initial_message')
    if initial_msg:
        data['initial_message'] = initial_msg
    data.setdefault('category', 'OTHER')
    data.setdefault('priority', 'MEDIUM')
    serializer = SupportTicketCreateSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    ticket = serializer.save(user=request.user)
    initial_message = serializer.validated_data.get('initial_message')
    if initial_message:
        SupportMessage.objects.create(ticket=ticket, sender=request.user, message=initial_message)
    out = SupportTicketSerializer(ticket)
    return Response(out.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def ticket_detail(request, ticket_id):
    """Get ticket detail with messages (only own tickets)."""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    if ticket.user_id != request.user.id:
        return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
    serializer = SupportTicketSerializer(ticket)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_required
def ticket_reply(request, ticket_id):
    """Add a reply (SupportMessage) to own ticket."""
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    if ticket.user_id != request.user.id:
        return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
    message = request.data.get('message', '').strip()
    if not message:
        return Response(
            {'error': 'Message is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    SupportMessage.objects.create(ticket=ticket, sender=request.user, message=message)
    serializer = SupportTicketSerializer(ticket)
    return Response(serializer.data)
