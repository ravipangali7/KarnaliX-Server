"""
User views for Activity Log.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from core.models import UserActivityLog
from core.serializers.user_serializers import UserActivityLogSerializer
from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def activity_log(request):
    """
    Get activity log for current user.
    """
    user = request.user
    
    action = request.query_params.get('action')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    queryset = UserActivityLog.objects.filter(user=user).order_by('-created_at')
    
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
