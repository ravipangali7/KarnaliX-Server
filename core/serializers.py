"""
DRF serializers for core models.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    User,
    UserRole,
    SuperSetting,
    SiteSetting,
    PaymentMode,
    Deposit,
    Withdraw,
    BonusRule,
    GameProvider,
    GameCategory,
    Game,
    GameLog,
    Transaction,
    ActivityLog,
    Message,
    Testimonial,
    CMSPage,
)


# --- Auth ---
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    whatsapp_number = serializers.CharField(required=False, allow_blank=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)


# --- User ---
class KycListSerializer(serializers.ModelSerializer):
    """For admin KYC list: user info + document URL for viewing."""
    user_username = serializers.CharField(source='username', read_only=True)
    status = serializers.CharField(source='kyc_status', read_only=True)
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'user_username', 'document_url', 'status', 'created_at']

    def get_document_url(self, obj):
        if not obj.kyc_document:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.kyc_document.url)
        return obj.kyc_document.url


class UserMinimalSerializer(serializers.ModelSerializer):
    """For list views and nested relations."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    kyc_status_display = serializers.CharField(source='get_kyc_status_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'kyc_status', 'kyc_status_display', 'is_active', 'created_at',
            'phone', 'whatsapp_number', 'commission_percentage', 'parent',
        ]
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    """List with aggregated balances for super/master (masters_balance, users_balance, etc.)."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    kyc_status_display = serializers.CharField(source='get_kyc_status_display', read_only=True)
    masters_balance = serializers.SerializerMethodField()
    masters_pl_balance = serializers.SerializerMethodField()
    users_balance = serializers.SerializerMethodField()
    players_count = serializers.SerializerMethodField()
    masters_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'kyc_status', 'kyc_status_display', 'is_active', 'created_at', 'pin',
            'masters_balance', 'masters_pl_balance', 'users_balance',
            'players_count', 'masters_count',
        ]

    def get_masters_balance(self, obj):
        if obj.role == UserRole.SUPER:
            return sum(c.main_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_masters_pl_balance(self, obj):
        if obj.role == UserRole.SUPER:
            return sum(c.pl_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_users_balance(self, obj):
        if obj.role == UserRole.MASTER:
            return sum(
                (u.main_balance or 0) for u in obj.children.filter(role=UserRole.PLAYER)
            )
        if obj.role == UserRole.SUPER:
            total = sum((m.main_balance or 0) for m in obj.children.filter(role=UserRole.MASTER))
            for m in obj.children.filter(role=UserRole.MASTER):
                total += sum((p.main_balance or 0) for p in m.children.filter(role=UserRole.PLAYER))
            return total
        return None

    def get_players_count(self, obj):
        if obj.role == UserRole.MASTER:
            return obj.children.filter(role=UserRole.PLAYER).count()
        if obj.role == UserRole.SUPER:
            return User.objects.filter(parent__parent=obj, role=UserRole.PLAYER).count()
        return None

    def get_masters_count(self, obj):
        if obj.role == UserRole.SUPER:
            return obj.children.filter(role=UserRole.MASTER).count()
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    kyc_status_display = serializers.CharField(source='get_kyc_status_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'email', 'phone', 'whatsapp_number',
            'role', 'role_display', 'commission_percentage', 'parent', 'referred_by',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'kyc_status', 'kyc_status_display', 'kyc_reject_reason', 'is_active',
            'created_at', 'updated_at', 'pin',
        ]
        read_only_fields = ['main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'kyc_status']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = User
        fields = [
            'username', 'password', 'name', 'email', 'phone', 'whatsapp_number',
            'commission_percentage', 'parent', 'role',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if password:
            user = User(**validated_data)
            user.set_password(password)
            user.save()
            return user
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# --- Me / Balances (for header) ---
class MeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    # Header balances by role (computed or same fields)
    main_balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    super_balance = serializers.SerializerMethodField()
    master_balance = serializers.SerializerMethodField()
    player_balance = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'bonus_balance', 'pl_balance', 'exposure_balance', 'exposure_limit',
            'super_balance', 'master_balance', 'player_balance', 'total_balance',
            'kyc_status', 'parent', 'whatsapp_number',
        ]

    def get_super_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.SUPER, parent=obj))
        return None

    def get_master_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.MASTER))
        if obj.role == UserRole.SUPER:
            return sum(c.main_balance for c in obj.children.filter(role=UserRole.MASTER))
        return None

    def get_player_balance(self, obj):
        if obj.role == UserRole.POWERHOUSE:
            return sum(c.main_balance for c in User.objects.filter(role=UserRole.PLAYER))
        if obj.role in (UserRole.SUPER, UserRole.MASTER):
            qs = User.objects.filter(role=UserRole.PLAYER)
            if obj.role == UserRole.MASTER:
                qs = qs.filter(parent=obj)
            else:
                qs = qs.filter(parent__parent=obj)
            return sum(c.main_balance for c in qs)
        return None

    def get_total_balance(self, obj):
        if obj.role == UserRole.PLAYER:
            return (obj.main_balance or 0) + (obj.bonus_balance or 0)
        main = obj.main_balance or 0
        sb = self.get_super_balance(obj) or 0
        mb = self.get_master_balance(obj) or 0
        pb = self.get_player_balance(obj) or 0
        return main + sb + mb + pb


# --- SuperSetting ---
class SuperSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperSetting
        fields = '__all__'


# --- SiteSetting ---
class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = '__all__'


# --- PaymentMode ---
class PaymentModeSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = PaymentMode
        fields = '__all__'


# --- Deposit ---
class DepositSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Deposit
        fields = '__all__'


class DepositCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['amount', 'payment_mode', 'screenshot', 'remarks']


# --- Withdraw ---
class WithdrawSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Withdraw
        fields = '__all__'


class WithdrawCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdraw
        fields = ['amount', 'payment_mode', 'screenshot', 'remarks']


# --- BonusRule ---
class BonusRuleSerializer(serializers.ModelSerializer):
    bonus_type_display = serializers.CharField(source='get_bonus_type_display', read_only=True)
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)

    class Meta:
        model = BonusRule
        fields = '__all__'


# --- GameProvider ---
class GameProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameProvider
        fields = '__all__'


# --- GameCategory ---
class GameCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GameCategory
        fields = '__all__'


# --- Game ---
class GameListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_code = serializers.CharField(source='provider.code', read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'game_uid', 'image', 'image_url', 'min_bet', 'max_bet', 'is_active',
            'category', 'category_name', 'provider', 'provider_name', 'provider_code',
            'created_at',
        ]


class GameDetailSerializer(serializers.ModelSerializer):
    category = GameCategorySerializer(read_only=True)
    provider = GameProviderSerializer(read_only=True)

    class Meta:
        model = Game
        fields = '__all__'


# --- GameLog ---
class GameLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    wallet_display = serializers.CharField(source='get_wallet_display', read_only=True)

    class Meta:
        model = GameLog
        fields = '__all__'


# --- Transaction ---
class TransactionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    wallet_display = serializers.CharField(source='get_wallet_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'


# --- ActivityLog ---
class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = '__all__'


# --- Message ---
class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['receiver', 'message', 'file', 'image']


# --- Testimonial ---
class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'


# --- CMSPage ---
class CMSPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CMSPage
        fields = '__all__'
