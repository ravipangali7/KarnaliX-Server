"""
User (role USER) KYC submit - POST document for verification.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import KYCVerification
from core.serializers.kyc_serializers import KYCVerificationCreateSerializer, KYCVerificationSerializer
from core.permissions import user_required


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_required
def submit_kyc(request):
    """
    POST: Submit KYC documents (multipart/form-data).
    document_type, document_number, document_front (file), document_back (file, optional).
    Rejects if user already has a PENDING or VERIFIED KYC.
    """
    user = request.user
    pending_or_verified = KYCVerification.objects.filter(
        user=user,
        status__in=[KYCVerification.Status.PENDING, KYCVerification.Status.VERIFIED]
    ).exists()
    if pending_or_verified:
        return Response(
            {'error': 'You already have a KYC submission pending or verified.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = KYCVerificationCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    kyc = serializer.save(user=user)
    out = KYCVerificationSerializer(kyc)
    return Response(out.data, status=status.HTTP_201_CREATED)
