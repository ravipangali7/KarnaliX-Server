"""
Powerhouse views for managing regular Users.
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
def user_list_create(request):
    """
    GET: List all Users
    POST: Create a new User
    """
    if request.method == 'GET':
        queryset = User.objects.filter(role='USER').order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        parent_id = request.query_params.get('parent_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(username__icontains=search) | queryset.filter(email__icontains=search)
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
            user = serializer.save()
            
            # Set parent (can be Powerhouse, Super, or Master)
            parent_id = request.data.get('parent_id')
            if parent_id:
                try:
                    parent = User.objects.get(id=parent_id, role__in=['POWERHOUSE', 'SUPER', 'MASTER'])
                    user.parent = parent
                except User.DoesNotExist:
                    pass
            user.save()
            
            return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_detail(request, user_id):
    """
    GET: Get User details
    PATCH: Update User
    DELETE: Deactivate User
    """
    try:
        user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
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
        return Response({'message': 'User deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_suspend(request, user_id):
    """Suspend a User."""
    try:
        user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'SUSPENDED'
    user.save()
    return Response({'message': 'User suspended'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_activate(request, user_id):
    """Activate a User."""
    try:
        user = User.objects.get(id=user_id, role='USER')
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user.status = 'ACTIVE'
    user.save()
    return Response({'message': 'User activated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_adjust_balance(request, user_id):
    """Adjust user wallet balance (deposit/withdraw by admin)."""
    from decimal import Decimal
    from core.models import WalletTransaction
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    amount = Decimal(str(request.data.get('amount', 0)))
    transaction_type = request.data.get('type', 'ADJUSTMENT')
    remarks = request.data.get('remarks', '')
    
    if amount == 0:
        return Response({'error': 'Amount must not be zero'}, status=status.HTTP_400_BAD_REQUEST)
    
    balance_before = user.wallet_balance
    user.wallet_balance += amount
    
    if user.wallet_balance < 0:
        return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.save()
    
    # Create transaction record
    WalletTransaction.objects.create(
        user=user,
        from_user=request.user if amount < 0 else None,
        to_user=user if amount > 0 else None,
        type=transaction_type,
        amount=abs(amount),
        balance_before=balance_before,
        balance_after=user.wallet_balance,
        remarks=remarks,
        created_by=request.user
    )
    
    return Response({
        'message': 'Balance adjusted successfully',
        'new_balance': str(user.wallet_balance)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_reset_password(request, user_id):
    """Reset password for a user. Body: { new_password: string }."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    new_password = request.data.get('new_password')
    if not new_password or len(new_password) < 6:
        return Response({'error': 'new_password required (min 6 characters)'}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(new_password)
    user.save(update_fields=['password'])
    return Response({'message': 'Password reset successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def user_show_pin(request, user_id):
    """Return the user's PIN (for privileged admin view)."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    if not user.pin:
        return Response({'error': 'No PIN set for this user'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'pin': user.pin})
