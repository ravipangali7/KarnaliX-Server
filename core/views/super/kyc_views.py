"""
Super views for KYC management.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import User, KYCVerification
from core.serializers.kyc_serializers import KYCVerificationSerializer
from core.permissions import super_required


def get_hierarchy_users(user):
    """Get all users in this Super's hierarchy."""
    if user.role == 'POWERHOUSE':
        return User.objects.all()
    else:
        return User.objects.filter(
            Q(id=user.id) | Q(parent=user) | Q(parent__parent=user)
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def kyc_list(request):
    """Get all KYC verifications for hierarchy users."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    queryset = KYCVerification.objects.filter(user__in=hierarchy_users).order_by('-submitted_at')
    
    # Filters
    status_filter = request.query_params.get('status')
    user_id = request.query_params.get('user_id')
    document_type = request.query_params.get('document_type')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if document_type:
        queryset = queryset.filter(document_type=document_type)
    if date_from:
        queryset = queryset.filter(submitted_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(submitted_at__date__lte=date_to)
    
    # Summary
    summary = {
        'total': queryset.count(),
        'pending': queryset.filter(status='PENDING').count(),
        'verified': queryset.filter(status='VERIFIED').count(),
        'rejected': queryset.filter(status='REJECTED').count(),
    }
    
    # Pagination
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = KYCVerificationSerializer(page_obj, many=True)
    
    return Response({
        'summary': summary,
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@super_required
def kyc_detail(request, kyc_id):
    """Get KYC verification details."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        kyc = KYCVerification.objects.get(id=kyc_id, user__in=hierarchy_users)
    except KYCVerification.DoesNotExist:
        return Response({'error': 'KYC not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = KYCVerificationSerializer(kyc)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def kyc_approve(request, kyc_id):
    """Approve KYC verification."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        kyc = KYCVerification.objects.get(id=kyc_id, user__in=hierarchy_users)
    except KYCVerification.DoesNotExist:
        return Response({'error': 'KYC not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if kyc.status != 'PENDING':
        return Response({'error': 'KYC is not pending'}, status=status.HTTP_400_BAD_REQUEST)
    
    kyc.status = 'VERIFIED'
    kyc.verified_by = user
    kyc.verified_at = timezone.now()
    kyc.save()
    
    return Response({
        'message': 'KYC approved successfully',
        'kyc': KYCVerificationSerializer(kyc).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@super_required
def kyc_reject(request, kyc_id):
    """Reject KYC verification."""
    user = request.user
    hierarchy_users = get_hierarchy_users(user)
    
    try:
        kyc = KYCVerification.objects.get(id=kyc_id, user__in=hierarchy_users)
    except KYCVerification.DoesNotExist:
        return Response({'error': 'KYC not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if kyc.status != 'PENDING':
        return Response({'error': 'KYC is not pending'}, status=status.HTTP_400_BAD_REQUEST)
    
    remarks = request.data.get('remarks', '').strip() or None
    kyc.status = 'REJECTED'
    kyc.verified_by = user
    kyc.verified_at = timezone.now()
    kyc.rejection_remarks = remarks
    kyc.save()
    
    return Response({
        'message': 'KYC rejected',
        'kyc': KYCVerificationSerializer(kyc).data
    })
