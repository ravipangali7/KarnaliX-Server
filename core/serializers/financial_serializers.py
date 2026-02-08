"""
Financial-related serializers for KarnaliX.
"""
from rest_framework import serializers
from core.models import WalletTransaction, PaymentMode, ClientRequest, Bonus, BonusRule


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions."""
    username = serializers.CharField(source='user.username', read_only=True)
    from_username = serializers.CharField(source='from_user.username', read_only=True, allow_null=True)
    to_username = serializers.CharField(source='to_user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'user', 'username', 'from_user', 'from_username',
            'to_user', 'to_username', 'type', 'amount',
            'balance_before', 'balance_after', 'reference_id',
            'remarks', 'created_at'
        ]


class PaymentModeSerializer(serializers.ModelSerializer):
    """Serializer for payment modes."""
    username = serializers.CharField(source='user.username', read_only=True)
    owner_role = serializers.CharField(source='user.role', read_only=True)
    qr_image_url = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMode
        fields = [
            'id', 'user', 'username', 'owner_role', 'wallet_holder_name', 'type',
            'wallet_phone', 'qr_image', 'qr_image_url', 'account_details', 'status', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']

    def get_qr_image_url(self, obj):
        if not obj.qr_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.qr_image.url)
        return obj.qr_image.url if obj.qr_image else None


class PaymentModeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment modes."""
    class Meta:
        model = PaymentMode
        fields = ['wallet_holder_name', 'type', 'wallet_phone', 'qr_image', 'account_details']


class ClientRequestSerializer(serializers.ModelSerializer):
    """Serializer for client requests (deposit/withdraw)."""
    username = serializers.CharField(source='user.username', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True, allow_null=True)
    payment_mode_details = PaymentModeSerializer(source='payment_mode', read_only=True)
    
    class Meta:
        model = ClientRequest
        fields = [
            'id', 'user', 'username', 'request_type', 'amount',
            'payment_mode', 'payment_mode_details', 'status',
            'processed_by', 'processed_by_username', 'processed_at',
            'screenshot', 'remarks', 'created_at'
        ]


class ClientRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating client requests."""
    class Meta:
        model = ClientRequest
        fields = ['request_type', 'amount', 'payment_mode', 'screenshot', 'remarks']


class ClientRequestActionSerializer(serializers.Serializer):
    """Serializer for approving/rejecting client requests."""
    remarks = serializers.CharField(required=False, allow_blank=True)


class BonusSerializer(serializers.ModelSerializer):
    """Serializer for bonuses."""
    username = serializers.CharField(source='user.username', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Bonus
        fields = [
            'id', 'user', 'username', 'bonus_type', 'amount',
            'rollover_requirement', 'status', 'granted_by',
            'granted_by_username', 'created_at', 'expired_at'
        ]


class BonusCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bonuses."""
    class Meta:
        model = Bonus
        fields = ['user', 'bonus_type', 'amount', 'rollover_requirement', 'expired_at']


class BonusRuleSerializer(serializers.ModelSerializer):
    """Serializer for bonus rules."""
    class Meta:
        model = BonusRule
        fields = [
            'id', 'name', 'bonus_type', 'percentage', 'max_bonus',
            'min_deposit', 'rollover_multiplier', 'is_active',
            'valid_from', 'valid_until', 'created_at'
        ]


class AccountStatementSerializer(serializers.Serializer):
    """Serializer for account statement summary."""
    total_deposit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_withdraw = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_bonus = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_bet = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_win = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transactions = WalletTransactionSerializer(many=True)
