"""
Super views for managing regular Users.
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
def user_list_create(request):
    """
    GET: List Users under this Super's hierarchy
    POST: Create a new User under this Super or their Masters
    """
    user = request.user
    
    if request.method == 'GET':
        if user.role == 'POWERHOUSE':
            queryset = User.objects.filter(role='USER')
        else:
            # Users directly under this Super or under Masters of this Super
            queryset = User.objects.filter(
                Q(role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
        
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
        data['role'] = 'USER'
        
        serializer = UserCreateSerializer(data=data)
        if serializer.is_valid():
            new_user = serializer.save()
            
            # Set parent (can be this Super or one of their Masters)
            parent_id = request.data.get('parent_id')
            if parent_id:
                try:
                    if user.role == 'POWERHOUSE':
                        parent = User.objects.get(id=parent_id, role__in=['SUPER', 'MASTER'])
                    else:
                        parent = User.objects.get(
                            Q(id=parent_id) & (Q(id=user.id) | Q(parent=user, role='MASTER'))
                        )
                    new_user.parent = parent
                except User.DoesNotExist:
                    new_user.parent = user
            else:
                new_user.parent = user
            
            new_user.save()
            
            return Response(UserDetailSerializer(new_user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@super_required
def user_detail(request, user_id):
    """
    GET: Get User details
    PATCH: Update User
    DELETE: Deactivate User
    """
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            target_user = User.objects.get(id=user_id, role='USER')
        else:
            target_user = User.objects.get(
                Q(id=user_id, role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserDetailSerializer(target_user)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = UserUpdateSerializer(target_user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserDetailSerializer(target_user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        target_user.status = 'CLOSED'
        target_user.save()
        return Response({'message': 'User deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def user_suspend(request, user_id):
    """Suspend a User."""
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            target_user = User.objects.get(id=user_id, role='USER')
        else:
            target_user = User.objects.get(
                Q(id=user_id, role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    target_user.status = 'SUSPENDED'
    target_user.save()
    return Response({'message': 'User suspended'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def user_activate(request, user_id):
    """Activate a User."""
    user = request.user
    
    try:
        if user.role == 'POWERHOUSE':
            target_user = User.objects.get(id=user_id, role='USER')
        else:
            target_user = User.objects.get(
                Q(id=user_id, role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    target_user.status = 'ACTIVE'
    target_user.save()
    return Response({'message': 'User activated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def user_reset_password(request, user_id):
    """Reset password for a user in Super's hierarchy."""
    user = request.user
    try:
        if user.role == 'POWERHOUSE':
            target_user = User.objects.get(id=user_id)
        else:
            target_user = User.objects.get(
                Q(id=user_id, role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    new_password = request.data.get('new_password')
    if not new_password or len(new_password) < 6:
        return Response({'error': 'new_password required (min 6 characters)'}, status=status.HTTP_400_BAD_REQUEST)
    target_user.set_password(new_password)
    target_user.save(update_fields=['password'])
    return Response({'message': 'Password reset successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def user_show_pin(request, user_id):
    """Return the user's PIN (for users in Super's hierarchy)."""
    user = request.user
    try:
        if user.role == 'POWERHOUSE':
            target_user = User.objects.get(id=user_id)
        else:
            target_user = User.objects.get(
                Q(id=user_id, role='USER') & (Q(parent=user) | Q(parent__parent=user))
            )
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    if not target_user.pin:
        return Response({'error': 'No PIN set for this user'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'pin': target_user.pin})
