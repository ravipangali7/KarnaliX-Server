"""
REST API for live chat: list chat partners and chat history.
Available to any authenticated user (USER, MASTER, SUPER, POWERHOUSE).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User, LiveChatMessage
from core.chat_utils import can_chat_with
from core.permissions import user_required


def _get_chat_partners(user):
    """Return list of users the current user can chat with."""
    partners = []
    role = getattr(user, 'role', None)
    parent = getattr(user, 'parent', None)

    if role == 'USER':
        if parent:
            partners.append({
                'id': parent.id,
                'username': parent.username,
                'role': parent.role,
            })
        return partners

    if role == 'MASTER':
        if parent:
            partners.append({
                'id': parent.id,
                'username': parent.username,
                'role': parent.role,
            })
        for child in user.children.filter(role='USER'):
            partners.append({
                'id': child.id,
                'username': child.username,
                'role': child.role,
            })
        return partners

    if role == 'SUPER':
        for child in user.children.filter(role='MASTER'):
            partners.append({
                'id': child.id,
                'username': child.username,
                'role': child.role,
            })
        return partners

    if role == 'POWERHOUSE':
        for child in user.children.filter(role='SUPER'):
            partners.append({
                'id': child.id,
                'username': child.username,
                'role': child.role,
            })
        return partners

    return partners


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def chat_partners(request):
    """List users the current user can chat with (parent for USER; parent + children for MASTER; children for SUPER/POWERHOUSE)."""
    partners = _get_chat_partners(request.user)
    return Response({'partners': partners})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def chat_history(request):
    """Paginated chat history with another user. Query param: other_user_id."""
    other_user_id = request.query_params.get('other_user_id')
    if not other_user_id:
        return Response({'error': 'other_user_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        other_user_id = int(other_user_id)
    except (TypeError, ValueError):
        return Response({'error': 'Invalid other_user_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if not can_chat_with(request.user, other_user):
        return Response({'error': 'Not allowed to chat with this user'}, status=status.HTTP_403_FORBIDDEN)

    queryset = LiveChatMessage.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user],
    ).order_by('created_at').select_related('sender', 'receiver')

    page = request.query_params.get('page', 1)
    page_size = min(int(request.query_params.get('page_size', 50) or 50), 100)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for m in page_obj:
        results.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_username': m.sender.username,
            'sender_role': m.sender.role,
            'receiver_id': m.receiver_id,
            'message': m.message,
            'created_at': m.created_at.isoformat(),
        })

    return Response({
        'results': results,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })
