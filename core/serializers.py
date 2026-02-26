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
    SliderSlide,
    Popup,
    LiveBettingSection,
    LiveBettingEvent,
    PaymentMode,
    Deposit,
    Withdraw,
    BonusRequest,
    BonusRule,
    GameProvider,
    GameCategory,
    Game,
    ComingSoonEnrollment,
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
    """Phone-first signup: requires signup_token (from verify-otp), phone, name, password."""
    signup_token = serializers.CharField()
    phone = serializers.CharField()
    name = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(required=False, allow_blank=True)


# --- User ---
class UserMinimalSerializer(serializers.ModelSerializer):
    """For list views and nested relations."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active', 'created_at',
            'phone', 'whatsapp_number', 'commission_percentage', 'parent',
        ]
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    """List with aggregated balances for super/master (masters_balance, users_balance, etc.)."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    masters_balance = serializers.SerializerMethodField()
    masters_pl_balance = serializers.SerializerMethodField()
    users_balance = serializers.SerializerMethodField()
    players_count = serializers.SerializerMethodField()
    masters_count = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    total_win_loss = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'role', 'role_display',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active', 'created_at', 'pin',
            'masters_balance', 'masters_pl_balance', 'users_balance',
            'players_count', 'masters_count',
            'total_balance', 'total_win_loss',
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

    def get_total_balance(self, obj):
        """For players: main + bonus + exposure."""
        if obj.role != UserRole.PLAYER:
            return None
        return (obj.main_balance or 0) + (obj.bonus_balance or 0) + (obj.exposure_balance or 0)

    def get_total_win_loss(self, obj):
        """For players: from annotated _win_sum - _lose_sum (see view annotate)."""
        if obj.role != UserRole.PLAYER:
            return None
        win = getattr(obj, '_win_sum', None)
        lose = getattr(obj, '_lose_sum', None)
        if win is None and lose is None:
            return None
        return (win or 0) - (lose or 0)


class UserDetailSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'email', 'phone', 'whatsapp_number',
            'role', 'role_display', 'commission_percentage', 'parent', 'referred_by',
            'main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance', 'exposure_limit',
            'is_active',
            'created_at', 'updated_at', 'pin',
        ]
        read_only_fields = ['main_balance', 'pl_balance', 'bonus_balance', 'exposure_balance']


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
            'parent', 'whatsapp_number',
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


# --- SliderSlide ---
class SliderSlideSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SliderSlide
        fields = [
            'id', 'title', 'subtitle', 'image', 'image_file',
            'cta_label', 'cta_link', 'order', 'created_at', 'updated_at',
        ]

    def get_image(self, obj):
        if obj.image_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image_file.url)
            return obj.image_file.url
        return (obj.image or '').strip() or None


# --- Popup ---
class PopupSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Popup
        fields = [
            'id', 'title', 'content', 'image', 'image_file',
            'cta_label', 'cta_link', 'is_active', 'order', 'created_at', 'updated_at',
        ]

    def get_image(self, obj):
        if obj.image_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image_file.url)
            return obj.image_file.url
        return (obj.image or '').strip() or None


# --- LiveBetting ---
class LiveBettingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveBettingEvent
        fields = '__all__'


class LiveBettingSectionSerializer(serializers.ModelSerializer):
    events = LiveBettingEventSerializer(many=True, read_only=True)

    class Meta:
        model = LiveBettingSection
        fields = '__all__'


# --- PaymentMode ---
class PaymentModeSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    qr_image_url = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PaymentMode
        fields = '__all__'

    def get_qr_image_url(self, obj):
        if not obj.qr_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.qr_image.url)
        return obj.qr_image.url


# --- Deposit ---
class DepositSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_mode_name = serializers.SerializerMethodField()
    payment_mode_qr_image = serializers.SerializerMethodField()
    payment_mode_detail = serializers.SerializerMethodField()

    class Meta:
        model = Deposit
        fields = '__all__'

    def get_payment_mode_name(self, obj):
        return obj.payment_mode.name if obj.payment_mode else None

    def get_payment_mode_qr_image(self, obj):
        if not obj.payment_mode or not obj.payment_mode.qr_image:
            return None
        request = self.context.get('request')
        url = obj.payment_mode.qr_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_payment_mode_detail(self, obj):
        if not obj.payment_mode:
            return None
        return PaymentModeSerializer(obj.payment_mode, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['payment_mode_detail'] = self.get_payment_mode_detail(instance)
        return ret


class DepositCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['amount', 'payment_mode', 'screenshot', 'remarks']


# --- Withdraw ---
class WithdrawSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_mode_name = serializers.SerializerMethodField()
    payment_mode_qr_image = serializers.SerializerMethodField()
    payment_mode_detail = serializers.SerializerMethodField()

    class Meta:
        model = Withdraw
        fields = '__all__'

    def get_payment_mode_name(self, obj):
        return obj.payment_mode.name if obj.payment_mode else None

    def get_payment_mode_qr_image(self, obj):
        if not obj.payment_mode or not obj.payment_mode.qr_image:
            return None
        request = self.context.get('request')
        url = obj.payment_mode.qr_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_payment_mode_detail(self, obj):
        if not obj.payment_mode:
            return None
        return PaymentModeSerializer(obj.payment_mode, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['payment_mode_detail'] = self.get_payment_mode_detail(instance)
        return ret


class WithdrawCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdraw
        fields = ['amount', 'payment_mode', 'screenshot', 'remarks']


# --- BonusRequest ---
class BonusRequestSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bonus_type_display = serializers.CharField(source='get_bonus_type_display', read_only=True)
    bonus_rule_name = serializers.SerializerMethodField()

    class Meta:
        model = BonusRequest
        fields = '__all__'

    def get_bonus_rule_name(self, obj):
        return obj.bonus_rule.name if obj.bonus_rule else None


class BonusRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusRequest
        fields = ['amount', 'bonus_type', 'bonus_rule', 'remarks']


# --- BonusRule ---
class BonusRuleSerializer(serializers.ModelSerializer):
    bonus_type_display = serializers.CharField(source='get_bonus_type_display', read_only=True)
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)

    class Meta:
        model = BonusRule
        fields = '__all__'


# --- GameProvider ---
class GameProviderSerializer(serializers.ModelSerializer):
    single_game_id = serializers.SerializerMethodField()

    class Meta:
        model = GameProvider
        fields = [
            'id', 'name', 'code', 'image', 'banner', 'api_endpoint', 'api_secret', 'api_token',
            'is_active', 'created_at', 'updated_at', 'single_game_id',
        ]

    def get_single_game_id(self, obj):
        qs = Game.objects.filter(provider=obj, is_active=True, is_single_game=True)
        if qs.count() == 1:
            return qs.values_list('id', flat=True).first()
        return None


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
            'is_coming_soon', 'coming_soon_launch_date', 'coming_soon_description',
            'is_single_game', 'created_at',
        ]


class GameDetailSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=GameCategory.objects.all())
    provider = serializers.PrimaryKeyRelatedField(queryset=GameProvider.objects.all())

    class Meta:
        model = Game
        fields = '__all__'


class ComingSoonGameSerializer(serializers.ModelSerializer):
    """For public coming-soon-games list: id, name, image, image_url, coming_soon_launch_date, coming_soon_description."""

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'image', 'image_url',
            'coming_soon_launch_date', 'coming_soon_description',
        ]


# --- ComingSoonEnrollment ---
class ComingSoonEnrollmentSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ComingSoonEnrollment
        fields = ['id', 'game', 'game_name', 'user', 'user_username', 'created_at']


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
