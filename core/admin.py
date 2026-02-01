from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    UserSettings,
    Wallet,
    Category,
    Provider,
    Game,
    Bet,
    Transaction,
    PaymentMethod,
    DepositRequest,
    WithdrawalRequest,
    Referral,
    ReferralTier,
    Bonus,
    PromoCode,
    PromoCodeRedemption,
    Ticket,
    TicketMessage,
    FAQ,
    FavoriteGame,
    PromoBanner,
    Announcement,
    AuditLog,
    SystemConfig,
)


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = True
    extra = 0


class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = True
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'name', 'role', 'status', 'is_kyc_verified',
        'is_active', 'date_joined',
    )
    list_filter = ('role', 'status', 'is_kyc_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'name', 'phone', 'referral_code')
    ordering = ('-date_joined',)
    inlines = [UserSettingsInline, WalletInline]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Profile',
            {
                'fields': (
                    'name', 'phone', 'whatsapp', 'dob', 'address', 'city', 'country', 'avatar',
                ),
            },
        ),
        (
            'Portal',
            {
                'fields': (
                    'referral_code', 'role', 'status',
                    'is_email_verified', 'is_phone_verified', 'is_kyc_verified',
                    'kyc_document', 'kyc_reject_reason',
                ),
            },
        ),
        (
            'Hierarchy',
            {
                'fields': ('created_by', 'assigned_master'),
            },
        ),
        (
            'Timestamps',
            {
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'language', 'dark_mode', 'two_factor_auth', 'updated_at')
    list_filter = ('dark_mode', 'two_factor_auth')
    search_fields = ('user__username', 'user__email')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'updated_at')
    search_fields = ('user__username', 'user__email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'game_count', 'color', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo', 'games_count', 'color', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'category', 'provider', 'min_bet', 'max_bet',
        'rating', 'is_hot', 'is_new', 'is_active', 'sort_order', 'created_at',
    )
    list_filter = ('is_active', 'is_hot', 'is_new', 'category', 'provider')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ('user', 'game_name', 'bet_amount', 'win_amount', 'status', 'bet_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'game_name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'amount', 'method', 'status', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('user__email', 'reference')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_limit', 'max_limit', 'has_qr', 'is_active', 'sort_order')
    list_filter = ('is_active',)


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'transaction_code')


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'reference')


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'email', 'status', 'earnings', 'created_at')
    list_filter = ('status',)
    search_fields = ('referrer__email', 'email', 'name')


@admin.register(ReferralTier)
class ReferralTierAdmin(admin.ModelAdmin):
    list_display = ('level', 'referrals_required', 'bonus_amount', 'per_referral_amount')


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'type', 'amount', 'status', 'expires_at', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('user__email', 'name')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'bonus_type', 'bonus_amount', 'uses_count', 'max_uses', 'is_active', 'expires_at')
    list_filter = ('bonus_type', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('-created_at',)


@admin.register(PromoCodeRedemption)
class PromoCodeRedemptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'promo_code', 'redeemed_at')
    list_filter = ('redeemed_at',)
    search_fields = ('user__email', 'promo_code__code')
    ordering = ('-redeemed_at',)


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'category', 'status', 'last_update_at', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('user__email', 'subject')
    inlines = [TicketMessageInline]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'is_staff', 'created_at')
    list_filter = ('is_staff',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('question', 'answer')


@admin.register(FavoriteGame)
class FavoriteGameAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'created_at')
    search_fields = ('user__email', 'game__name')


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'start_at', 'end_at', 'sort_order', 'created_at')
    list_filter = ('is_active',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'start_at', 'end_at', 'created_at')
    list_filter = ('is_active',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'action', 'entity_type', 'entity_id', 'ip_address', 'created_at')
    list_filter = ('entity_type',)
    search_fields = ('action', 'entity_type', 'entity_id')
    readonly_fields = ('admin_user', 'action', 'entity_type', 'entity_id', 'payload', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at', 'updated_by')
    search_fields = ('key',)
