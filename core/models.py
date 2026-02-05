from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal


# =============================================================================
# USER MODEL WITH HIERARCHY
# =============================================================================

class User(AbstractUser):
    """
    Custom User model with role-based hierarchy.
    Hierarchy: POWERHOUSE → SUPER → MASTER → USER
    """
    
    class Role(models.TextChoices):
        POWERHOUSE = 'POWERHOUSE', 'Powerhouse'
        SUPER = 'SUPER', 'Super'
        MASTER = 'MASTER', 'Master'
        USER = 'USER', 'User'
        STAFF = 'STAFF', 'Staff'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CLOSED = 'CLOSED', 'Closed'
    
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text='Hierarchy parent (POWERHOUSE→SUPER→MASTER→USER)'
    )
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )
    wallet_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    exposure_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    last_login_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.role})"


# =============================================================================
# FINANCIAL SYSTEM
# =============================================================================

class WalletTransaction(models.Model):
    """All money movements in the system."""
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAW = 'WITHDRAW', 'Withdraw'
        BONUS = 'BONUS', 'Bonus'
        BET_PLACED = 'BET_PLACED', 'Bet Placed'
        BET_SETTLED = 'BET_SETTLED', 'Bet Settled'
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
        TRANSFER = 'TRANSFER', 'Transfer'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='outgoing_transactions')
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transactions')
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    reference_id = models.CharField(max_length=100, blank=True, null=True, help_text='Reference like bet_id or bonus_id')
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.amount}"


class PaymentMode(models.Model):
    """Payment methods configured by users."""
    
    class PaymentType(models.TextChoices):
        BANK = 'BANK', 'Bank Transfer'
        UPI = 'UPI', 'UPI'
        EWALLET = 'EWALLET', 'E-Wallet'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_modes')
    wallet_holder_name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PaymentType.choices)
    wallet_phone = models.CharField(max_length=20, blank=True)
    qr_image = models.ImageField(upload_to='payment_qr/', blank=True, null=True)
    account_details = models.JSONField(default=dict, blank=True, help_text='Bank account details as JSON')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Payment Mode'
        verbose_name_plural = 'Payment Modes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.wallet_holder_name}"


class ClientRequest(models.Model):
    """Deposit and Withdraw requests from clients."""
    
    class RequestType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAW = 'WITHDRAW', 'Withdraw'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_requests')
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_mode = models.ForeignKey(PaymentMode, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_requests')
    processed_at = models.DateTimeField(null=True, blank=True)
    screenshot = models.ImageField(upload_to='request_screenshots/', blank=True, null=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Client Request'
        verbose_name_plural = 'Client Requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.request_type} - {self.amount} ({self.status})"


class Bonus(models.Model):
    """Bonus grants to users."""
    
    class BonusType(models.TextChoices):
        WELCOME = 'WELCOME', 'Welcome Bonus'
        MANUAL = 'MANUAL', 'Manual Bonus'
        CASHBACK = 'CASHBACK', 'Cashback'
        REFERRAL = 'REFERRAL', 'Referral Bonus'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        AVAILABLE = 'AVAILABLE', 'Available'
        COMPLETED = 'COMPLETED', 'Completed'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bonuses')
    bonus_type = models.CharField(max_length=20, choices=BonusType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    rollover_requirement = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_bonuses')
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Bonus'
        verbose_name_plural = 'Bonuses'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.bonus_type} - {self.amount}"


class BonusRule(models.Model):
    """Configurable bonus rules/templates."""
    
    class BonusType(models.TextChoices):
        WELCOME = 'WELCOME', 'Welcome Bonus'
        DEPOSIT = 'DEPOSIT', 'Deposit Bonus'
        CASHBACK = 'CASHBACK', 'Cashback'
        REFERRAL = 'REFERRAL', 'Referral Bonus'
    
    name = models.CharField(max_length=255)
    promo_code = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text='Optional code for users to apply this rule')
    bonus_type = models.CharField(max_length=20, choices=BonusType.choices)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text='Bonus percentage of deposit')
    max_bonus = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text='Maximum bonus amount')
    min_deposit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text='Minimum deposit to qualify')
    rollover_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'), help_text='Wagering requirement multiplier')
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Bonus Rule'
        verbose_name_plural = 'Bonus Rules'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.bonus_type}) - {self.percentage}%"


# =============================================================================
# GAME SYSTEM
# =============================================================================

class GameProvider(models.Model):
    """External game providers."""
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    api_endpoint = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Game Provider'
        verbose_name_plural = 'Game Providers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Game(models.Model):
    """Individual games from providers."""
    
    class GameType(models.TextChoices):
        SPORTS = 'SPORTS', 'Sports'
        CASINO = 'CASINO', 'Casino'
        SLOT = 'SLOT', 'Slot'
        LIVE = 'LIVE', 'Live'
        VIRTUAL = 'VIRTUAL', 'Virtual'
        CRASH = 'CRASH', 'Crash'
        OTHER = 'OTHER', 'Other'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        DISABLED = 'DISABLED', 'Disabled'
    
    provider = models.ForeignKey(GameProvider, on_delete=models.CASCADE, related_name='games')
    name = models.CharField(max_length=255)
    game_type = models.CharField(max_length=20, choices=GameType.choices)
    min_bet = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('10.00'))
    max_bet = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('100000.00'))
    rtp = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('96.00'), help_text='Return to Player percentage')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"


class Bet(models.Model):
    """User bets on games."""
    
    class Result(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        WON = 'WON', 'Won'
        LOST = 'LOST', 'Lost'
        VOID = 'VOID', 'Void'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bets')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='bets')
    provider_bet_id = models.CharField(max_length=100, blank=True)
    bet_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    odds = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    possible_win = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)
    win_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    placed_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Bet'
        verbose_name_plural = 'Bets'
        ordering = ['-placed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.game.name} - {self.bet_amount} ({self.result})"


class GameTransactionLog(models.Model):
    """Logs of transactions with game providers."""
    
    class TransactionType(models.TextChoices):
        BET = 'BET', 'Bet'
        WIN = 'WIN', 'Win'
        REFUND = 'REFUND', 'Refund'
        ROLLBACK = 'ROLLBACK', 'Rollback'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_transaction_logs')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='transaction_logs')
    provider = models.ForeignKey(GameProvider, on_delete=models.CASCADE, related_name='transaction_logs')
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    provider_bet_id = models.CharField(max_length=100, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    round = models.CharField(max_length=100, blank=True)
    match = models.CharField(max_length=255, blank=True)
    bet_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    win_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    before_balance = models.DecimalField(max_digits=15, decimal_places=2)
    after_balance = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Game Transaction Log'
        verbose_name_plural = 'Game Transaction Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.provider_transaction_id}"


# =============================================================================
# KYC SYSTEM
# =============================================================================

class KYCVerification(models.Model):
    """KYC document verification."""
    
    class DocumentType(models.TextChoices):
        ID = 'ID', 'National ID'
        PASSPORT = 'PASSPORT', 'Passport'
        LICENSE = 'LICENSE', 'Driving License'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_verifications')
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_number = models.CharField(max_length=100)
    document_front = models.ImageField(upload_to='kyc_documents/')
    document_back = models.ImageField(upload_to='kyc_documents/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_kycs')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_remarks = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'KYC Verification'
        verbose_name_plural = 'KYC Verifications'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.document_type} ({self.status})"


# =============================================================================
# SUPPORT SYSTEM
# =============================================================================

class SupportTicket(models.Model):
    """Support tickets from users."""
    
    class Category(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        TECHNICAL = 'TECHNICAL', 'Technical'
        ACCOUNT = 'ACCOUNT', 'Account'
        OTHER = 'OTHER', 'Other'
    
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
    
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.id} - {self.subject} ({self.status})"


class SupportMessage(models.Model):
    """Messages in support tickets."""
    
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_messages')
    message = models.TextField()
    attachment_url = models.FileField(upload_to='support_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Support Message'
        verbose_name_plural = 'Support Messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message on Ticket #{self.ticket.id} by {self.sender.username}"


# =============================================================================
# LIVE CHAT (real-time WebSocket)
# =============================================================================

class LiveChatMessage(models.Model):
    """Real-time live chat messages between hierarchy pairs (user-master, master-super, etc.)."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_chat_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_chat_received')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Live Chat Message'
        verbose_name_plural = 'Live Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['receiver', 'sender']),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} at {self.created_at}"


# =============================================================================
# SETTINGS
# =============================================================================

class SuperSetting(models.Model):
    """Settings for SUPER role users, controlled by POWERHOUSE."""
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='super_setting',
        limit_choices_to={'role': User.Role.SUPER}
    )
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    max_credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    bet_limit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Super Setting'
        verbose_name_plural = 'Super Settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}"


# =============================================================================
# ACTIVITY LOGS
# =============================================================================

class UserActivityLog(models.Model):
    """Audit trail for user actions."""
    
    class Action(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        BET_PLACED = 'BET_PLACED', 'Bet Placed'
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', 'Password Changed'
        PROFILE_UPDATED = 'PROFILE_UPDATED', 'Profile Updated'
        DEPOSIT_REQUEST = 'DEPOSIT_REQUEST', 'Deposit Request'
        WITHDRAW_REQUEST = 'WITHDRAW_REQUEST', 'Withdraw Request'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=Action.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.created_at}"


# =============================================================================
# ROLE PERMISSIONS
# =============================================================================

class RolePermission(models.Model):
    """Module-level permissions per role."""
    
    role = models.CharField(max_length=20, choices=User.Role.choices)
    module_name = models.CharField(max_length=100)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        unique_together = ['role', 'module_name']
        ordering = ['role', 'module_name']
    
    def __str__(self):
        return f"{self.role} - {self.module_name}"


# =============================================================================
# SITE CONTENT (public website content: hero, promos, testimonials, coming_soon)
# =============================================================================

class SiteContent(models.Model):
    """Key-value store for public website content (hero, promos, testimonials, coming_soon)."""
    key = models.CharField(max_length=50, unique=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Content'
        verbose_name_plural = 'Site Content'
        ordering = ['key']

    def __str__(self):
        return self.key
