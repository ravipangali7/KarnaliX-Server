"""
Powerhouse views for Super Settings management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal

from core.models import SuperSetting, User
from core.serializers.user_serializers import SuperSettingSerializer
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def settings_list(request):
    """
    Get all Super settings.
    """
    queryset = SuperSetting.objects.all().select_related('user')
    
    # Filters
    status_filter = request.query_params.get('status')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    serializer = SuperSettingSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def settings_detail(request, user_id):
    """
    GET: Get Super settings for a specific Super user
    PATCH: Update Super settings
    """
    try:
        user = User.objects.get(id=user_id, role='SUPER')
    except User.DoesNotExist:
        return Response({'error': 'Super user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get or create settings
    setting, created = SuperSetting.objects.get_or_create(user=user)
    
    if request.method == 'GET':
        serializer = SuperSettingSerializer(setting)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        # Update fields
        if 'commission_rate' in request.data:
            setting.commission_rate = Decimal(str(request.data['commission_rate']))
        if 'max_credit_limit' in request.data:
            setting.max_credit_limit = Decimal(str(request.data['max_credit_limit']))
        if 'bet_limit' in request.data:
            setting.bet_limit = Decimal(str(request.data['bet_limit']))
        if 'status' in request.data:
            setting.status = request.data['status']
        
        setting.save()
        
        return Response(SuperSettingSerializer(setting).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def settings_create(request, user_id):
    """
    Create Super settings for a Super user (if not exists).
    """
    try:
        user = User.objects.get(id=user_id, role='SUPER')
    except User.DoesNotExist:
        return Response({'error': 'Super user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if hasattr(user, 'super_setting'):
        return Response({'error': 'Settings already exist for this user'}, status=status.HTTP_400_BAD_REQUEST)
    
    setting = SuperSetting.objects.create(
        user=user,
        commission_rate=Decimal(str(request.data.get('commission_rate', 0))),
        max_credit_limit=Decimal(str(request.data.get('max_credit_limit', 0))),
        bet_limit=Decimal(str(request.data.get('bet_limit', 0))),
        status=request.data.get('status', 'ACTIVE')
    )
    
    return Response(SuperSettingSerializer(setting).data, status=status.HTTP_201_CREATED)
