"""
Master views for Client Activity Log.
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import User, UserActivityLog
from core.serializers.user_serializers import UserActivityLogSerializer
from core.permissions import master_required


def get_hierarchy_users(user):
    """Get users under this Master."""
    if user.role in ['POWERHOUSE', 'SUPER']:
        return User.objects.all()
    else:
        return User.objects.filter(Q(id=user.id) | Q(parent=user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def activity_log_list(request):
    """
    Get activity logs for users under this Master.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    queryset = UserActivityLog.objects.filter(user__in=hierarchy_users).order_by('-created_at')
    
    # Filters
    user_id = request.query_params.get('user_id')
    action = request.query_params.get('action')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = UserActivityLogSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@master_required
def user_activity_log(request, user_id):
    """
    Get activity logs for a specific user.
    """
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        target_user = hierarchy_users.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    queryset = UserActivityLog.objects.filter(user=target_user).order_by('-created_at')
    
    # Filters
    action = request.query_params.get('action')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = UserActivityLogSerializer(page_obj, many=True)
    
    return Response({
        'user': {
            'id': target_user.id,
            'username': target_user.username,
        },
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })
