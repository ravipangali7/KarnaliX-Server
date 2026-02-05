"""
Master views for Profile management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import User
from core.serializers.user_serializers import UserDetailSerializer, ProfileUpdateSerializer
from core.permissions import master_required


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@master_required
def profile(request):
    """
    GET: Get current user's profile
    PATCH: Update current user's profile
    """
    user = request.user
    
    if request.method == 'GET':
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        # Only allow updating certain fields
        allowed_fields = ['phone', 'email']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        # Check if email is being changed and is unique
        new_email = data.get('email')
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exists():
                return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProfileUpdateSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserDetailSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@master_required
def change_password(request):
    """
    Change current user's password.
    """
    user = request.user
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    
    if not old_password or not new_password:
        return Response(
            {'error': 'Old password and new password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(old_password):
        return Response(
            {'error': 'Old password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(new_password) < 6:
        return Response(
            {'error': 'New password must be at least 6 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': 'Password changed successfully'})
