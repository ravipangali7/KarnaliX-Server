"""
User (role USER) profile views - GET/PATCH profile.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import User, KYCVerification
from core.serializers.user_serializers import ProfileUpdateSerializer
from core.permissions import user_required


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@user_required
def profile(request):
    """
    GET: Current user profile (USER role).
    PATCH: Update phone, email (allowed fields).
    """
    user = request.user

    if request.method == 'GET':
        kyc_verified = KYCVerification.objects.filter(
            user=user, status=KYCVerification.Status.VERIFIED
        ).exists()
        kyc_pending = KYCVerification.objects.filter(
            user=user, status=KYCVerification.Status.PENDING
        ).exists()
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'status': user.status,
            'wallet_balance': str(user.wallet_balance),
            'exposure_balance': str(user.exposure_balance),
            'created_at': user.created_at,
            'last_login_at': user.last_login_at,
            'vip_level': (user.settings or {}).get('vip_level', 'Gold'),
            'is_kyc_verified': kyc_verified,
            'is_kyc_pending': kyc_pending,
        }
        return Response(data)

    elif request.method == 'PATCH':
        allowed_fields = ['phone', 'email']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        new_email = data.get('email')
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exists():
                return Response(
                    {'error': 'Email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = ProfileUpdateSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone or '',
                'role': user.role,
                'status': user.status,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
