"""
Powerhouse views for Support Ticket management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import SupportTicket, SupportMessage
from core.serializers.support_serializers import (
    SupportTicketSerializer, SupportTicketListSerializer,
    SupportTicketUpdateSerializer, SupportMessageSerializer
)
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def ticket_list(request):
    """
    Get all support tickets.
    """
    queryset = SupportTicket.objects.all().order_by('-created_at')
    
    # Filters
    status_filter = request.query_params.get('status')
    category = request.query_params.get('category')
    priority = request.query_params.get('priority')
    user_id = request.query_params.get('user_id')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if category:
        queryset = queryset.filter(category=category)
    if priority:
        queryset = queryset.filter(priority=priority)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # Summary
    summary = {
        'total': queryset.count(),
        'open': queryset.filter(status='OPEN').count(),
        'in_progress': queryset.filter(status='IN_PROGRESS').count(),
        'resolved': queryset.filter(status='RESOLVED').count(),
        'high_priority': queryset.filter(priority='HIGH', status__in=['OPEN', 'IN_PROGRESS']).count(),
    }
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = SupportTicketListSerializer(page_obj, many=True)
    
    return Response({
        'summary': summary,
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def ticket_detail(request, ticket_id):
    """
    GET: Get ticket details with messages
    PATCH: Update ticket status/priority/assignment
    """
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = SupportTicketSerializer(ticket)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = SupportTicketUpdateSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(SupportTicketSerializer(ticket).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def ticket_reply(request, ticket_id):
    """
    Reply to a support ticket.
    """
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    message_text = request.data.get('message', '').strip()
    if not message_text:
        return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create message
    message = SupportMessage.objects.create(
        ticket=ticket,
        sender=request.user,
        message=message_text
    )
    
    # Update ticket status to IN_PROGRESS if it was OPEN
    if ticket.status == 'OPEN':
        ticket.status = 'IN_PROGRESS'
        ticket.save()
    
    return Response({
        'message': SupportMessageSerializer(message).data,
        'ticket': SupportTicketSerializer(ticket).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def ticket_close(request, ticket_id):
    """
    Close a support ticket.
    """
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    ticket.status = 'CLOSED'
    ticket.save()
    
    return Response({
        'message': 'Ticket closed',
        'ticket': SupportTicketSerializer(ticket).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def ticket_assign(request, ticket_id):
    """
    Assign ticket to a user.
    """
    from core.models import User
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    assigned_to_id = request.data.get('assigned_to')
    if assigned_to_id:
        try:
            assigned_to = User.objects.get(id=assigned_to_id)
            ticket.assigned_to = assigned_to
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        ticket.assigned_to = None
    
    ticket.save()
    
    return Response({
        'message': 'Ticket assigned',
        'ticket': SupportTicketSerializer(ticket).data
    })
