"""
KYC-related serializers for KarnaliX.
"""
from rest_framework import serializers
from core.models import KYCVerification


class KYCVerificationSerializer(serializers.ModelSerializer):
    """Serializer for KYC verifications."""
    username = serializers.CharField(source='user.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = KYCVerification
        fields = [
            'id', 'user', 'username', 'document_type', 'document_number',
            'document_front', 'document_back', 'status',
            'verified_by', 'verified_by_username', 'verified_at',
            'rejection_remarks', 'submitted_at'
        ]


class KYCVerificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating KYC verifications."""
    class Meta:
        model = KYCVerification
        fields = ['document_type', 'document_number', 'document_front', 'document_back']


class KYCActionSerializer(serializers.Serializer):
    """Serializer for KYC approval/rejection."""
    remarks = serializers.CharField(required=False, allow_blank=True)
