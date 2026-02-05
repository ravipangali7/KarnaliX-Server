"""
Powerhouse views for managing Master users.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User
from core.serializers.user_serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer, UserUpdateSerializer
)
from core.permissions import powerhouse_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def master_list_create(request):
    """
    GET: List all Master users
    POST: Create a new Master user
    """
    if request.method == 'GET':
        queryset = User.objects.filter(role='MASTER').order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        parent_id = request.query_params.get('parent_id')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(username__icontains=search) | queryset.filter(email__icontains=search)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        
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
        data['role'] = 'MASTER'
        
        serializer = UserCreateSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Set parent (can be Powerhouse or Super)
            parent_id = request.data.get('parent_id')
            if parent_id:
                try:
                    parent = User.objects.get(id=parent_id, role__in=['POWERHOUSE', 'SUPER'])
                    user.parent = parent
                except User.DoesNotExist:
                    user.parent = request.user
            else:
                user.parent = request.user
            user.save()
            
            return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def master_detail(request, user_id):
    """
    GET: Get Master user details
    PATCH: Update Master user
    DELETE: Deactivate Master user
    """
    try:
        user = User.objects.get(id=user_id, role='MASTER')
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
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
        return Response({'message': 'Master user deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def master_suspend(request, user_id):
    """Suspend a Master user."""
    try:
        user = User.objects.get(id=user_id, role='MASTER')
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'SUSPENDED'
    user.save()
    return Response({'message': 'Master user suspended'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def master_activate(request, user_id):
    """Activate a Master user."""
    try:
        user = User.objects.get(id=user_id, role='MASTER')
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'ACTIVE'
    user.save()
    return Response({'message': 'Master user activated'})
