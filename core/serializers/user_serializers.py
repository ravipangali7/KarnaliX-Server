"""
User-related serializers for KarnaliX.
"""
import random
import string
from rest_framework import serializers
from core.models import User, SuperSetting, UserActivityLog, ClientRequest


def generate_pin():
    """Generate a 6-digit numeric PIN."""
    return ''.join(random.choices(string.digits, k=6))


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list views."""
    parent_username = serializers.CharField(source='parent.username', read_only=True, allow_null=True)
    children_count = serializers.SerializerMethodField()
    pin_masked = serializers.SerializerMethodField()
    total_deposit = serializers.SerializerMethodField()
    total_withdrawal = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role', 'status',
            'wallet_balance', 'exposure_balance', 'parent_username',
            'children_count', 'pin_masked', 'total_deposit', 'total_withdrawal',
            'created_at', 'last_login_at'
        ]

    def get_children_count(self, obj):
        return obj.children.count()

    def get_pin_masked(self, obj):
        if obj.pin:
            return '****'
        return ''

    def get_total_deposit(self, obj):
        from django.db.models import Sum
        agg = ClientRequest.objects.filter(
            user=obj, request_type='DEPOSIT', status='APPROVED'
        ).aggregate(total=Sum('amount'))
        return str(agg['total'] or 0)

    def get_total_withdrawal(self, obj):
        from django.db.models import Sum
        agg = ClientRequest.objects.filter(
            user=obj, request_type='WITHDRAW', status='APPROVED'
        ).aggregate(total=Sum('amount'))
        return str(agg['total'] or 0)


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user detail views."""
    parent = UserListSerializer(read_only=True)
    pin_masked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role', 'status',
            'wallet_balance', 'exposure_balance', 'parent', 'pin_masked',
            'created_at', 'updated_at', 'last_login_at'
        ]

    def get_pin_masked(self, obj):
        if obj.pin:
            return '****'
        return ''


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if not user.pin:
            user.pin = generate_pin()
            user.save(update_fields=['pin'])
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating users."""
    class Meta:
        model = User
        fields = ['phone', 'status']


class SuperSettingSerializer(serializers.ModelSerializer):
    """Serializer for Super settings."""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = SuperSetting
        fields = [
            'id', 'user', 'username', 'commission_rate',
            'max_credit_limit', 'bet_limit', 'status', 'updated_at'
        ]
        read_only_fields = ['user', 'updated_at']


class UserActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for user activity logs."""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserActivityLog
        fields = ['id', 'user', 'username', 'action', 'ip_address', 'device_info', 'created_at']


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for profile updates."""
    class Meta:
        model = User
        fields = ['phone', 'email']
