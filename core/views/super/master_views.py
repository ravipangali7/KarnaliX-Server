"""
Super views for managing Master users.
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User
from core.serializers.user_serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer, UserUpdateSerializer
)
from core.permissions import super_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@super_required
def master_list_create(request):
    """
    GET: List Master users under this Super
    POST: Create a new Master user under this Super
    """
    user = request.user
    
    if request.method == 'GET':
        if user.role == 'POWERHOUSE':
            queryset = User.objects.filter(role='MASTER')
        else:
            queryset = User.objects.filter(role='MASTER', parent=user)
        
        queryset = queryset.order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        parent_id = request.query_params.get('parent_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
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
            master = serializer.save()
            master.parent = user
            master.save()
            
            return Response(UserDetailSerializer(master).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@super_required
def master_detail(request, user_id):
    """
    GET: Get Master user details
    PATCH: Update Master user
    DELETE: Deactivate Master user
    """
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            master = User.objects.get(id=user_id, role='MASTER')
        else:
            master = User.objects.get(id=user_id, role='MASTER', parent=user)
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserDetailSerializer(master)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = UserUpdateSerializer(master, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserDetailSerializer(master).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        master.status = 'CLOSED'
        master.save()
        return Response({'message': 'Master user deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def master_suspend(request, user_id):
    """Suspend a Master user."""
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            master = User.objects.get(id=user_id, role='MASTER')
        else:
            master = User.objects.get(id=user_id, role='MASTER', parent=user)
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    master.status = 'SUSPENDED'
    master.save()
    return Response({'message': 'Master user suspended'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def master_activate(request, user_id):
    """Activate a Master user."""
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            master = User.objects.get(id=user_id, role='MASTER')
        else:
            master = User.objects.get(id=user_id, role='MASTER', parent=user)
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    
    master.status = 'ACTIVE'
    master.save()
    return Response({'message': 'Master user activated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def master_reset_password(request, user_id):
    """Reset password for a Master user in Super's hierarchy."""
    user = request.user
    try:
        if user.role == 'POWERHOUSE':
            master = User.objects.get(id=user_id, role='MASTER')
        else:
            master = User.objects.get(id=user_id, role='MASTER', parent=user)
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    new_password = request.data.get('new_password')
    if not new_password or len(new_password) < 6:
        return Response({'error': 'new_password required (min 6 characters)'}, status=status.HTTP_400_BAD_REQUEST)
    master.set_password(new_password)
    master.save(update_fields=['password'])
    return Response({'message': 'Password reset successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def master_show_pin(request, user_id):
    """Return the Master user's PIN."""
    user = request.user
    try:
        if user.role == 'POWERHOUSE':
            master = User.objects.get(id=user_id, role='MASTER')
        else:
            master = User.objects.get(id=user_id, role='MASTER', parent=user)
    except User.DoesNotExist:
        return Response({'error': 'Master user not found'}, status=status.HTTP_404_NOT_FOUND)
    if not master.pin:
        return Response({'error': 'No PIN set for this user'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'pin': master.pin})
