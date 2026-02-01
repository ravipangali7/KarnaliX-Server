from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for gaming portal with KYC, referral, and hierarchy.
    
    Role Hierarchy (highest to lowest):
    - POWERHOUSE: Platform owner with absolute authority (root level)
    - SUPER_ADMIN: Platform management
    - MASTER: Agent/Operator who manages users
    - USER: Player/End user
    """

    class Role(models.TextChoices):
        USER = 'user', 'User'
        MASTER = 'master', 'Master'
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        POWERHOUSE = 'powerhouse', 'PowerHouse'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        BANNED = 'banned', 'Banned'
        PENDING = 'pending', 'Pending'

    # Role hierarchy levels for permission checks
    ROLE_HIERARCHY = {
        'powerhouse': 4,
        'super_admin': 3,
        'master': 2,
        'user': 1,
    }

    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    dob = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    referral_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    
    # Hierarchy fields
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
    )
    
    # Role-specific limits
    transfer_limit = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Maximum coins this user can transfer (for Masters)'
    )
    betting_limit = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Maximum bet amount allowed (for Users)'
    )
    
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    kyc_document = models.JSONField(default=dict, blank=True)  # flexible for multiple docs
    kyc_reject_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users'
    )
    assigned_master = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_user'

    def get_role_level(self):
        """Get the hierarchy level of this user's role."""
        return self.ROLE_HIERARCHY.get(self.role, 0)

    def can_manage(self, other_user):
        """Check if this user can manage another user based on role hierarchy."""
        return self.get_role_level() > other_user.get_role_level()

    def is_powerhouse(self):
        """Check if user has PowerHouse role."""
        return self.role == self.Role.POWERHOUSE

    def is_super_admin(self):
        """Check if user has SuperAdmin role or higher."""
        return self.role in [self.Role.SUPER_ADMIN, self.Role.POWERHOUSE]

    def is_master(self):
        """Check if user has Master role or higher."""
        return self.role in [self.Role.MASTER, self.Role.SUPER_ADMIN, self.Role.POWERHOUSE]

    def get_subordinates(self):
        """Get all users created by or assigned to this user."""
        if self.role == self.Role.POWERHOUSE:
            # PowerHouse can see all users
            return User.objects.exclude(pk=self.pk)
        elif self.role == self.Role.SUPER_ADMIN:
            # SuperAdmin can see Masters and Users
            return User.objects.filter(
                models.Q(role__in=[self.Role.MASTER, self.Role.USER]) |
                models.Q(parent=self) |
                models.Q(created_by=self)
            ).distinct()
        elif self.role == self.Role.MASTER:
            # Master can see only their assigned users
            return User.objects.filter(
                models.Q(assigned_master=self) |
                models.Q(created_by=self) |
                models.Q(parent=self)
            ).filter(role=self.Role.USER).distinct()
        return User.objects.none()


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    promotional_emails = models.BooleanField(default=False)
    two_factor_auth = models.BooleanField(default=False)
    biometric_login = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='en')
    currency = models.CharField(max_length=10, default='INR')
    timezone = models.CharField(max_length=50, default='UTC')
    deposit_limit = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    session_limit = models.PositiveIntegerField(null=True, blank=True)
    betting_limit = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    self_exclusion = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_user_settings'


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='INR')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_wallet'


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=255, blank=True)
    href = models.CharField(max_length=255, blank=True)
    game_count = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_category'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Provider(models.Model):
    name = models.CharField(max_length=100)
    logo = models.CharField(max_length=500, blank=True)  # URL or path
    color = models.CharField(max_length=50, blank=True)
    games_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_provider'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Game(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='games')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='games')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    image = models.CharField(max_length=500, blank=True)  # URL or path
    players = models.PositiveIntegerField(default=0)
    min_bet = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_bet = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    rtp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_hot = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    how_to_play = models.JSONField(default=list, blank=True)  # list of strings
    features = models.JSONField(default=list, blank=True)  # list of strings
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_game'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Bet(models.Model):
    class BetStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bets')
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True, related_name='bets')
    game_name = models.CharField(max_length=200)
    game_type = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)
    bet_amount = models.DecimalField(max_digits=14, decimal_places=2)
    win_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    odds = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=BetStatus.choices, default=BetStatus.PENDING)
    bet_at = models.DateTimeField(auto_now_add=True)
    settled_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='settled_bets'
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_bet'
        ordering = ['-bet_at']


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = 'deposit', 'Deposit'
        WITHDRAWAL = 'withdrawal', 'Withdrawal'
        BET = 'bet', 'Bet'
        WIN = 'win', 'Win'
        BONUS = 'bonus', 'Bonus'
        REFUND = 'refund', 'Refund'
        TRANSFER = 'transfer', 'Transfer'

    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_transaction'
        ordering = ['-created_at']


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=500, blank=True)
    min_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    has_qr = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_payment_method'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class DepositRequest(models.Model):
    class DepositStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposit_requests')
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.CASCADE, related_name='deposit_requests'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_code = models.CharField(max_length=100, blank=True)
    receipt_file_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=DepositStatus.choices, default=DepositStatus.PENDING)
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_deposits'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_deposit_request'
        ordering = ['-created_at']


class WithdrawalRequest(models.Model):
    class WithdrawalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PROCESSING = 'processing', 'Processing'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_requests')
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.CASCADE, related_name='withdrawal_requests'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    account_number = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING
    )
    reference = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_withdrawals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_withdrawal_request'
        ordering = ['-created_at']


class Referral(models.Model):
    class ReferralStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        JOINED = 'joined', 'Joined'
        ACTIVE = 'active', 'Active'

    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals')
    referred_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='referred_by'
    )
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ReferralStatus.choices, default=ReferralStatus.PENDING)
    earnings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_bets = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_referral'
        ordering = ['-created_at']


class ReferralTier(models.Model):
    level = models.PositiveIntegerField(unique=True)
    referrals_required = models.PositiveIntegerField()
    bonus_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    per_referral_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_referral_tier'
        ordering = ['level']


class BonusType(models.TextChoices):
    """Shared bonus types for Bonus and PromoCode models."""
    WELCOME = 'welcome', 'Welcome'
    DEPOSIT = 'deposit', 'Deposit'
    REFERRAL = 'referral', 'Referral'
    CASHBACK = 'cashback', 'Cashback'
    OTHER = 'other', 'Other'


class Bonus(models.Model):
    class BonusStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        WAGERED = 'wagered', 'Wagered'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bonuses')
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=BonusType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    wagering = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    wagering_progress = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=BonusStatus.choices, default=BonusStatus.PENDING)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_bonus'
        ordering = ['-created_at']
        verbose_name_plural = 'Bonuses'


class PromoCode(models.Model):
    """Promotional codes that can be redeemed for bonuses."""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200, blank=True)
    bonus_type = models.CharField(max_length=20, choices=BonusType.choices, default=BonusType.OTHER)
    bonus_amount = models.DecimalField(max_digits=15, decimal_places=2)
    wagering_requirement = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    max_uses = models.IntegerField(default=0)  # 0 = unlimited
    uses_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_promo_code'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.bonus_amount}"


class PromoCodeRedemption(models.Model):
    """Tracks which users have redeemed which promo codes."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_redemptions')
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='redemptions')
    bonus = models.ForeignKey(Bonus, on_delete=models.SET_NULL, null=True, related_name='promo_redemption')
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_promo_code_redemption'
        unique_together = ['user', 'promo_code']

    def __str__(self):
        return f"{self.user.username} - {self.promo_code.code}"


class Ticket(models.Model):
    class TicketStatus(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    last_update_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_ticket'
        ordering = ['-last_update_at']


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_messages')
    message = models.TextField()
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_ticket_message'
        ordering = ['created_at']


class FAQ(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_faq'
        ordering = ['sort_order', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'


class FavoriteGame(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_games')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_favorite_game'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'game'], name='unique_user_game_favorite')
        ]


class PromoBanner(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    link_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_promo_banner'
        ordering = ['sort_order', '-created_at']


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_announcement'
        ordering = ['-created_at']


class AuditLog(models.Model):
    admin_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_audit_log'
        ordering = ['-created_at']


class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='config_updates'
    )

    class Meta:
        db_table = 'core_system_config'
        verbose_name = 'System Config'
        verbose_name_plural = 'System Configs'

    def __str__(self):
        return self.key


class Testimonial(models.Model):
    """User testimonials for homepage display."""
    name = models.CharField(max_length=100)
    avatar = models.CharField(max_length=10, blank=True)  # e.g., "RK"
    location = models.CharField(max_length=100, blank=True)
    game = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    message = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_testimonial'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.game}"
