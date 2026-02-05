"""
Powerhouse views for managing Super users.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User, SuperSetting
from core.serializers.user_serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer, UserUpdateSerializer
)
from core.permissions import powerhouse_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def super_list_create(request):
    """
    GET: List all Super users
    POST: Create a new Super user
    """
    if request.method == 'GET':
        queryset = User.objects.filter(role='SUPER').order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(username__icontains=search) | queryset.filter(email__icontains=search)
        
        # Pagination
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = UserListSerializer(page_obj, many=True)
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['role'] = 'SUPER'
        
        serializer = UserCreateSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            user.parent = request.user
            user.save()
            
            # Create default SuperSetting
            SuperSetting.objects.create(user=user)
            
            return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def super_detail(request, user_id):
    """
    GET: Get Super user details
    PATCH: Update Super user
    DELETE: Deactivate Super user
    """
    try:
        user = User.objects.get(id=user_id, role='SUPER')
    except User.DoesNotExist:
        return Response({'error': 'Super user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserDetailSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        user.status = 'CLOSED'
        user.save()
        return Response({'message': 'Super user deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def super_suspend(request, user_id):
    """Suspend a Super user."""
    try:
        user = User.objects.get(id=user_id, role='SUPER')
    except User.DoesNotExist:
        return Response({'error': 'Super user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'SUSPENDED'
    user.save()
    return Response({'message': 'Super user suspended'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def super_activate(request, user_id):
    """Activate a Super user."""
    try:
        user = User.objects.get(id=user_id, role='SUPER')
    except User.DoesNotExist:
        return Response({'error': 'Super user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'ACTIVE'
    user.save()
    return Response({'message': 'Super user activated'})
