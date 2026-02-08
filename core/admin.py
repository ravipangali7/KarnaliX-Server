from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, WalletTransaction, PaymentMode, ClientRequest, Bonus, BonusRule,
    GameProvider, Game, Bet, GameTransactionLog, KYCVerification,
    SupportTicket, SupportMessage, LiveChatMessage,
    SuperSetting, UserActivityLog, RolePermission, SiteContent
)


# =============================================================================
# USER ADMIN
# =============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for User model."""

    list_display = ['username', 'email', 'phone', 'role', 'parent', 'wallet_balance', 'exposure_balance', 'status', 'created_at']
    list_filter = ['role', 'status', 'is_active', 'is_staff', 'created_at']
    search_fields = ['username', 'email', 'phone', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_login_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Platform Info', {
            'fields': ('phone', 'role', 'parent', 'referred_by', 'status')
        }),
        ('Balance', {
            'fields': ('wallet_balance', 'exposure_balance')
        }),
        ('Timestamps', {
            'fields': ('last_login_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Platform Info', {
            'fields': ('phone', 'role', 'parent', 'referred_by', 'status')
        }),
    )


# =============================================================================
# FINANCIAL ADMIN
# =============================================================================

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Admin for WalletTransaction model."""

    list_display = ['id', 'user', 'type', 'amount', 'from_user', 'to_user', 'balance_before', 'balance_after', 'created_by', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['user__username', 'user__email', 'reference_id', 'remarks', 'from_user__username', 'to_user__username']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['user', 'created_by', 'from_user', 'to_user']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    def has_change_permission(self, request, obj=None):
        return False  # Transactions should be immutable
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentMode)
class PaymentModeAdmin(admin.ModelAdmin):
    """Admin for PaymentMode model."""

    list_display = ['id', 'user', 'type', 'wallet_holder_name', 'wallet_phone', 'status', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['user__username', 'wallet_holder_name', 'wallet_phone']
    raw_id_fields = ['user']


@admin.register(ClientRequest)
class ClientRequestAdmin(admin.ModelAdmin):
    """Admin for ClientRequest model."""

    list_display = ['id', 'user', 'request_type', 'amount', 'payment_mode', 'status', 'processed_by', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'remarks']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['user', 'processed_by', 'payment_mode']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Info', {
            'fields': ('user', 'request_type', 'amount', 'payment_mode', 'screenshot')
        }),
        ('Processing', {
            'fields': ('status', 'processed_by', 'processed_at', 'remarks')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    """Admin for Bonus model."""

    list_display = ['id', 'user', 'bonus_type', 'amount', 'rollover_requirement', 'status', 'granted_by', 'created_at']
    list_filter = ['bonus_type', 'status', 'created_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user', 'granted_by']
    date_hierarchy = 'created_at'


@admin.register(BonusRule)
class BonusRuleAdmin(admin.ModelAdmin):
    """Admin for BonusRule model."""

    list_display = ['id', 'name', 'bonus_type', 'percentage', 'max_bonus', 'min_deposit', 'rollover_multiplier', 'is_active', 'valid_from', 'valid_until']
    list_filter = ['bonus_type', 'is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active', 'percentage', 'max_bonus', 'min_deposit']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'bonus_type', 'is_active')
        }),
        ('Bonus Configuration', {
            'fields': ('percentage', 'max_bonus', 'min_deposit', 'rollover_multiplier')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# GAME ADMIN
# =============================================================================

@admin.register(GameProvider)
class GameProviderAdmin(admin.ModelAdmin):
    """Admin for GameProvider model."""

    list_display = ['id', 'name', 'code', 'api_endpoint', 'status', 'game_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at']

    @admin.display(description='Games')
    def game_count(self, obj):
        return obj.games.count()


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin for Game model."""

    list_display = ['id', 'name', 'provider', 'game_type', 'min_bet', 'max_bet', 'rtp', 'status', 'created_at']
    list_filter = ['game_type', 'status', 'provider', 'created_at']
    search_fields = ['name', 'provider__name']
    raw_id_fields = ['provider']
    list_editable = ['min_bet', 'max_bet', 'rtp']


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    """Admin for Bet model. Only result, win_amount, and settled_at are editable."""

    list_display = ['id', 'user', 'game', 'bet_amount', 'odds', 'possible_win', 'result', 'win_amount', 'placed_at']
    list_filter = ['result', 'game__game_type', 'placed_at']
    search_fields = ['user__username', 'game__name', 'provider_bet_id']
    readonly_fields = ['id', 'user', 'game', 'provider_bet_id', 'bet_amount', 'odds', 'possible_win', 'placed_at']
    raw_id_fields = ['user', 'game']
    date_hierarchy = 'placed_at'
    list_per_page = 50

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GameTransactionLog)
class GameTransactionLogAdmin(admin.ModelAdmin):
    """Admin for GameTransactionLog model."""

    list_display = ['id', 'user', 'game', 'provider', 'transaction_type', 'bet_amount', 'win_amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'provider', 'created_at']
    search_fields = ['user__username', 'provider_transaction_id', 'provider_bet_id']
    readonly_fields = ['id', 'created_at', 'provider_raw_data']
    raw_id_fields = ['user', 'game', 'provider']
    date_hierarchy = 'created_at'
    list_per_page = 50

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# KYC ADMIN
# =============================================================================

@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    """Admin for KYCVerification model."""

    list_display = ['id', 'user', 'document_type', 'document_number', 'status', 'verified_by', 'submitted_at']
    list_filter = ['document_type', 'status', 'submitted_at']
    search_fields = ['user__username', 'user__email', 'document_number']
    readonly_fields = ['submitted_at']
    raw_id_fields = ['user', 'verified_by']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Document', {
            'fields': ('document_type', 'document_number', 'document_front', 'document_back')
        }),
        ('Verification', {
            'fields': ('status', 'verified_by', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# SUPPORT ADMIN
# =============================================================================

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1
    readonly_fields = ['created_at']
    raw_id_fields = ['sender']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    """Admin for SupportTicket model."""

    list_display = ['id', 'subject', 'user', 'category', 'priority', 'status', 'assigned_to', 'message_count', 'created_at']
    list_filter = ['category', 'priority', 'status', 'created_at']
    search_fields = ['subject', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'assigned_to']
    inlines = [SupportMessageInline]
    date_hierarchy = 'created_at'

    @admin.display(description='Messages')
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    """Admin for SupportMessage model."""

    list_display = ['id', 'ticket', 'sender', 'short_message', 'created_at']
    list_filter = ['created_at']
    search_fields = ['ticket__subject', 'sender__username', 'message']
    readonly_fields = ['created_at']
    raw_id_fields = ['ticket', 'sender']

    @admin.display(description='Message')
    def short_message(self, obj):
        text = (obj.message or '')[:50]
        return f'{text}...' if len(obj.message or '') > 50 else text


@admin.register(LiveChatMessage)
class LiveChatMessageAdmin(admin.ModelAdmin):
    """Admin for LiveChatMessage model."""

    list_display = ['id', 'sender', 'receiver', 'short_message', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sender__username', 'receiver__username', 'message']
    readonly_fields = ['created_at']
    raw_id_fields = ['sender', 'receiver']
    date_hierarchy = 'created_at'

    @admin.display(description='Message')
    def short_message(self, obj):
        text = (obj.message or '')[:50]
        return f'{text}...' if len(obj.message or '') > 50 else text


# =============================================================================
# SETTINGS ADMIN
# =============================================================================

@admin.register(SuperSetting)
class SuperSettingAdmin(admin.ModelAdmin):
    """Admin for SuperSetting model."""

    list_display = ['user', 'commission_rate', 'max_credit_limit', 'bet_limit', 'status', 'updated_at']
    list_filter = ['status', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['updated_at']
    raw_id_fields = ['user']


# =============================================================================
# ACTIVITY LOG ADMIN
# =============================================================================

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """Admin for UserActivityLog model (read-only)."""

    list_display = ['id', 'user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = ['id', 'user', 'action', 'ip_address', 'device_info', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# ROLE PERMISSION ADMIN
# =============================================================================

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin for RolePermission model."""

    list_display = ['role', 'module_name', 'can_view', 'can_create', 'can_edit', 'can_delete']
    list_filter = ['role', 'can_view', 'can_create', 'can_edit', 'can_delete']
    search_fields = ['module_name']
    list_editable = ['can_view', 'can_create', 'can_edit', 'can_delete']
    ordering = ['role', 'module_name']


# =============================================================================
# SITE CONTENT ADMIN
# =============================================================================

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    """Admin for SiteContent model (hero, promos, FAQ, contact, terms, privacy)."""

    list_display = ['key', 'updated_at']
    search_fields = ['key']
    readonly_fields = ['updated_at']
