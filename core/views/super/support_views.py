"""
Super views for Support Ticket management.
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User, SupportTicket, SupportMessage
from core.serializers.support_serializers import (
    SupportTicketSerializer, SupportTicketListSerializer,
    SupportTicketUpdateSerializer, SupportMessageSerializer
)
from core.permissions import super_required


def get_hierarchy_users(user):
    """Get all users in this Super's hierarchy."""
    if user.role == 'POWERHOUSE':
        return User.objects.all()
    else:
        return User.objects.filter(
            Q(id=user.id) | Q(parent=user) | Q(parent__parent=user)
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def ticket_list(request):
    """Get all support tickets for hierarchy users."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    queryset = SupportTicket.objects.filter(user__in=hierarchy_users).order_by('-created_at')
    
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
@super_required
def ticket_detail(request, ticket_id):
    """
    GET: Get ticket details with messages
    PATCH: Update ticket status/priority/assignment
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id, user__in=hierarchy_users)
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
@super_required
def ticket_reply(request, ticket_id):
    """Reply to a support ticket."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id, user__in=hierarchy_users)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    message_text = request.data.get('message', '').strip()
    if not message_text:
        return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    message = SupportMessage.objects.create(
        ticket=ticket,
        sender=user,
        message=message_text
    )
    
    if ticket.status == 'OPEN':
        ticket.status = 'IN_PROGRESS'
        ticket.save()
    
    return Response({
        'message': SupportMessageSerializer(message).data,
        'ticket': SupportTicketSerializer(ticket).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def ticket_close(request, ticket_id):
    """Close a support ticket."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        ticket = SupportTicket.objects.get(id=ticket_id, user__in=hierarchy_users)
    except SupportTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
    
    ticket.status = 'CLOSED'
    ticket.save()
    
    return Response({
        'message': 'Ticket closed',
        'ticket': SupportTicketSerializer(ticket).data
    })
