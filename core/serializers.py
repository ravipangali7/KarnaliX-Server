"""
Serializers for games, categories, providers, promo banners, and other core models.
"""
from rest_framework import serializers
from .models import (
    Category, Provider, Game, PromoBanner, User, Wallet, Transaction,
    DepositRequest, WithdrawalRequest, Bet, Ticket, TicketMessage,
    PaymentMethod, SystemConfig, Bonus, UserSettings, Testimonial, ReferralTier,
    PromoCode, PromoCodeRedemption, Referral, FAQ, Announcement, AuditLog,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'href', 'game_count',
            'color', 'sort_order', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'logo', 'color', 'games_count', 'sort_order',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GameSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'slug', 'name', 'image', 'category', 'category_name', 'category_slug',
            'provider', 'provider_name', 'players', 'min_bet', 'max_bet', 'rating', 'rtp',
            'is_hot', 'is_new', 'is_active', 'description', 'how_to_play', 'features', 'sort_order',
        ]


class PromoBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoBanner
        fields = [
            'id', 'title', 'description', 'image_url', 'link_url', 'sort_order',
            'is_active', 'start_at', 'end_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with essential fields."""
    wallet_balance = serializers.DecimalField(
        source='wallet.balance', max_digits=14, decimal_places=2, read_only=True, default=0
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'phone', 'role', 'status',
            'is_active', 'is_kyc_verified', 'kyc_document', 'referral_code',
            'wallet_balance', 'date_joined', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at', 'referral_code']


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'username', 'balance', 'currency', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'username', 'type', 'amount', 'method',
            'reference', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model."""
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'icon', 'min_limit', 'max_limit',
            'has_qr', 'is_active', 'sort_order', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepositRequestSerializer(serializers.ModelSerializer):
    """Serializer for DepositRequest model."""
    username = serializers.CharField(source='user.username', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = DepositRequest
        fields = [
            'id', 'user', 'username', 'payment_method', 'payment_method_name',
            'amount', 'transaction_code', 'receipt_file_url', 'status',
            'approved_by', 'approved_by_username', 'approved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'approved_by', 'approved_at', 'created_at', 'updated_at']


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for WithdrawalRequest model."""
    username = serializers.CharField(source='user.username', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'user', 'username', 'payment_method', 'payment_method_name',
            'amount', 'account_number', 'account_name', 'status', 'reference',
            'approved_by', 'approved_by_username', 'approved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'approved_by', 'approved_at', 'created_at', 'updated_at']


class BetSerializer(serializers.ModelSerializer):
    """Serializer for Bet model."""
    username = serializers.CharField(source='user.username', read_only=True)
    settled_by_username = serializers.CharField(source='settled_by.username', read_only=True)

    class Meta:
        model = Bet
        fields = [
            'id', 'user', 'username', 'game', 'game_name', 'game_type',
            'category', 'bet_amount', 'win_amount', 'odds', 'status',
            'bet_at', 'settled_by', 'settled_by_username', 'settled_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'settled_by', 'settled_at', 'created_at', 'updated_at']


class TicketMessageSerializer(serializers.ModelSerializer):
    """Serializer for TicketMessage model."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'ticket', 'user', 'username', 'message', 'is_staff', 'created_at']
        read_only_fields = ['id', 'created_at']


class TicketSerializer(serializers.ModelSerializer):
    """Serializer for Ticket model."""
    username = serializers.CharField(source='user.username', read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'username', 'subject', 'category', 'status',
            'messages', 'last_update_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_update_at', 'created_at', 'updated_at']


class SystemConfigSerializer(serializers.ModelSerializer):
    """Serializer for SystemConfig model."""
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = SystemConfig
        fields = ['id', 'key', 'value', 'updated_at', 'updated_by', 'updated_by_username']
        read_only_fields = ['id', 'updated_at']


class BonusSerializer(serializers.ModelSerializer):
    """Serializer for Bonus model."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Bonus
        fields = [
            'id', 'user', 'username', 'name', 'type', 'amount',
            'wagering', 'wagering_progress', 'expires_at', 'status',
            'description', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PromoCodeSerializer(serializers.ModelSerializer):
    """Serializer for PromoCode model."""
    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'name', 'bonus_type', 'bonus_amount',
            'wagering_requirement', 'max_uses', 'uses_count',
            'is_active', 'expires_at', 'created_at',
        ]
        read_only_fields = ['id', 'uses_count', 'created_at']


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for UserSettings model."""
    class Meta:
        model = UserSettings
        fields = [
            'id', 'user', 'email_notifications', 'push_notifications',
            'sms_notifications', 'promotional_emails', 'two_factor_auth',
            'biometric_login', 'dark_mode', 'language', 'currency',
            'timezone', 'deposit_limit', 'session_limit', 'betting_limit',
            'self_exclusion', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class TestimonialSerializer(serializers.ModelSerializer):
    """Serializer for Testimonial model."""
    class Meta:
        model = Testimonial
        fields = [
            'id', 'name', 'avatar', 'location', 'game', 'amount',
            'message', 'rating', 'sort_order', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ReferralTierSerializer(serializers.ModelSerializer):
    """Serializer for ReferralTier model."""
    class Meta:
        model = ReferralTier
        fields = [
            'id', 'level', 'referrals_required', 'bonus_amount',
            'per_referral_amount', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReferralSerializer(serializers.ModelSerializer):
    """Serializer for Referral model."""
    referrer_username = serializers.CharField(source='referrer.username', read_only=True)
    referred_username = serializers.CharField(source='referred_user.username', read_only=True)

    class Meta:
        model = Referral
        fields = [
            'id', 'referrer', 'referrer_username', 'referred_user', 'referred_username',
            'name', 'email', 'joined_at', 'status', 'earnings', 'total_bets',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQ model."""
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'sort_order',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for Announcement model."""
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'body', 'is_active', 'start_at', 'end_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'admin_user', 'admin_username', 'action', 'entity_type',
            'entity_id', 'payload', 'ip_address', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PromoCodeRedemptionSerializer(serializers.ModelSerializer):
    """Serializer for PromoCodeRedemption model."""
    username = serializers.CharField(source='user.username', read_only=True)
    promo_code_code = serializers.CharField(source='promo_code.code', read_only=True)

    class Meta:
        model = PromoCodeRedemption
        fields = [
            'id', 'user', 'username', 'promo_code', 'promo_code_code',
            'bonus', 'redeemed_at',
        ]
        read_only_fields = ['id', 'redeemed_at']
