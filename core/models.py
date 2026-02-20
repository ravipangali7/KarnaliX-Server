from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# --- Choices (TextChoices) ---

class UserRole(models.TextChoices):
    POWERHOUSE = 'powerhouse', 'Powerhouse'
    SUPER = 'super', 'Super'
    MASTER = 'master', 'Master'
    PLAYER = 'player', 'Player'


class KycStatus(models.TextChoices):
    APPROVED = 'approved', 'Approved'
    PENDING = 'pending', 'Pending'
    REJECTED = 'rejected', 'Rejected'


class PaymentModeType(models.TextChoices):
    EWALLET = 'ewallet', 'E-Wallet'
    BANK = 'bank', 'Bank'


class PaymentModeStatus(models.TextChoices):
    APPROVED = 'approved', 'Approved'
    PENDING = 'pending', 'Pending'
    REJECTED = 'rejected', 'Rejected'


class RequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    CANCELLED = 'cancelled', 'Cancelled'


class BonusType(models.TextChoices):
    WELCOME = 'welcome', 'Welcome'
    DEPOSIT = 'deposit', 'Deposit'
    REFERRAL = 'referral', 'Referral'


class RewardType(models.TextChoices):
    FLAT = 'flat', 'Flat'
    PERCENTAGE = 'percentage', 'Percentage'


class GameLogWallet(models.TextChoices):
    MAIN_BALANCE = 'main_balance', 'Main Balance'
    BONUS_BALANCE = 'bonus_balance', 'Bonus Balance'


class GameLogType(models.TextChoices):
    WIN = 'win', 'Win'
    BET = 'bet', 'Bet'
    LOSE = 'lose', 'Lose'
    DRAW = 'draw', 'Draw'


class TransactionActionType(models.TextChoices):
    IN = 'in', 'In'
    OUT = 'out', 'Out'


class TransactionWallet(models.TextChoices):
    MAIN_BALANCE = 'main_balance', 'Main Balance'
    BONUS_BALANCE = 'bonus_balance', 'Bonus Balance'
    PL_BALANCE = 'pl_balance', 'P/L Balance'
    EXPOSURE_BALANCE = 'exposure_balance', 'Exposure Balance'


class TransactionType(models.TextChoices):
    DEPOSIT = 'deposit', 'Deposit'
    WITHDRAW = 'withdraw', 'Withdraw'
    BONUS = 'bonus', 'Bonus'
    BET_PLACED = 'bet_placed', 'Bet Placed'
    TRANSFER = 'transfer', 'Transfer'
    PL = 'pl', 'P/L'
    EXPOSURE = 'exposure', 'Exposure'
    SETTLEMENT = 'settlement', 'Settlement'


class TransactionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'


class ActivityAction(models.TextChoices):
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'
    BET_PLACED = 'bet_placed', 'Bet Placed'
    PASSWORD_CHANGE = 'password_change', 'Password Change'
    PROFILE_UPDATE = 'profile_update', 'Profile Update'
    KYC_REQUEST = 'kyc_request', 'KYC Request'
    DEPOSIT_REQUEST = 'deposit_request', 'Deposit Request'
    WITHDRAW_REQUEST = 'withdraw_request', 'Withdraw Request'
    MESSAGE = 'message', 'Message'
    TRANSFER_COIN = 'transfer_coin', 'Transfer Coin'


def default_decimal_zero():
    return Decimal('0.00')


# --- 1. SuperSetting ---

class SuperSetting(models.Model):
    """Global system settings: GGR, API, limits, default exposure (see Exposure Logic #1)."""
    ggr_coin = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    game_api_url = models.URLField(blank=True)
    game_api_secret = models.CharField(max_length=255, blank=True)
    game_api_token = models.CharField(max_length=255, blank=True)
    game_api_callback_url = models.URLField(blank=True)
    game_api_domain_url = models.URLField(blank=True)
    game_api_launch_url = models.URLField(blank=True)
    min_withdraw = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    min_deposit = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    max_withdraw = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    max_deposit = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    exposure_limit = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Super Setting'
        verbose_name_plural = 'Super Settings'

    def __str__(self):
        return f"SuperSetting (id={self.pk})"

    @classmethod
    def get_settings(cls):
        """Return the single SuperSetting instance, or None if none exists."""
        return cls.objects.first()


# --- 2. User (AbstractUser) ---

class User(AbstractUser):
    """
    User with role hierarchy (powerhouse > super > master > player), balances,
    KYC, and referral. Exposure limit default from SuperSetting on create (Exposure Logic #1).
    """
    first_name = None
    last_name = None
    
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.PLAYER
    )
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp_number = models.CharField(max_length=50, blank=True)
    pin = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00')
    )
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )
    main_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    pl_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    bonus_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    exposure_balance = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    exposure_limit = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def save(self, *args, **kwargs):
        # Exposure Logic #1: new user gets default exposure_limit from SuperSetting
        if self._state.adding:
            if self.exposure_limit is None or self.exposure_limit == 0:
                settings = SuperSetting.get_settings()
                if settings is not None:
                    self.exposure_limit = settings.exposure_limit
        if self.exposure_limit is None:
            self.exposure_limit = Decimal('0.00')
        super().save(*args, **kwargs)

    @property
    def total_display_balance(self):
        """Main + bonus for display (e.g. player header)."""
        return (self.main_balance or Decimal('0')) + (self.bonus_balance or Decimal('0'))

    def can_use_bonus_for_game(self, min_bet):
        """Bonus Logic #2: bonus only when main is 0 or below min_bet for that game."""
        if min_bet is None:
            min_bet = Decimal('0')
        return (self.main_balance or Decimal('0')) <= 0 or (self.main_balance or Decimal('0')) < min_bet

    def __str__(self):
        return self.username or str(self.pk)


# --- 3. PaymentMode ---

class PaymentMode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_modes'
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PaymentModeType.choices)
    wallet_phone = models.CharField(max_length=50, blank=True)
    qr_image = models.ImageField(upload_to='payment_qr/', blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True)
    bank_branch = models.CharField(max_length=255, blank=True)
    bank_account_no = models.CharField(max_length=100, blank=True)
    bank_account_holder_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PaymentModeStatus.choices,
        default=PaymentModeStatus.PENDING
    )
    reject_reason = models.TextField(blank=True)
    action_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_modes_acted_on'
    )
    action_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Mode'
        verbose_name_plural = 'Payment Modes'

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


# --- 4. Deposit ---

class Deposit(models.Model):
    """
    Deposit request. On approval: parent's main_balance deducted, user's main_balance
    added (Deposit & Withdraw Logic). Create dual transactions per Transaction Logic.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deposits'
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_mode = models.ForeignKey(
        PaymentMode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deposits'
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    reject_reason = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deposits_processed'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    screenshot = models.ImageField(upload_to='deposit_screenshots/', blank=True, null=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deposit'
        verbose_name_plural = 'Deposits'

    def __str__(self):
        return f"Deposit #{self.pk} - {self.user} - {self.amount} ({self.status})"


# --- 5. Withdraw ---

class Withdraw(models.Model):
    """
    Withdrawal request. On approval: user's main_balance deducted, parent's main_balance
    added (Deposit & Withdraw Logic). KYC must be approved for player before withdraw (Security #6).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_mode = models.ForeignKey(
        PaymentMode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawals'
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    reject_reason = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawals_processed'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    screenshot = models.ImageField(upload_to='withdraw_screenshots/', blank=True, null=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Withdraw'
        verbose_name_plural = 'Withdrawals'

    def __str__(self):
        return f"Withdraw #{self.pk} - {self.user} - {self.amount} ({self.status})"


# --- 6. BonusRule ---

class BonusRule(models.Model):
    name = models.CharField(max_length=255)
    bonus_type = models.CharField(max_length=20, choices=BonusType.choices)
    promo_code = models.CharField(max_length=100, blank=True, null=True)
    reward_type = models.CharField(max_length=20, choices=RewardType.choices)
    reward_amount = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    roll_required = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bonus Rule'
        verbose_name_plural = 'Bonus Rules'

    def __str__(self):
        return f"{self.name} ({self.get_bonus_type_display()})"


# --- 7. GameProvider ---

class GameProvider(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    api_endpoint = models.URLField(blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    api_token = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Game Provider'
        verbose_name_plural = 'Game Providers'

    def __str__(self):
        return f"{self.name} ({self.code})"


# --- 8. GameCategory ---

class GameCategory(models.Model):
    name = models.CharField(max_length=255)
    svg = models.FileField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Game Category'
        verbose_name_plural = 'Game Categories'

    def __str__(self):
        return self.name


# --- 9. Game ---

class Game(models.Model):
    provider = models.ForeignKey(
        GameProvider,
        on_delete=models.CASCADE,
        related_name='games'
    )
    category = models.ForeignKey(
        GameCategory,
        on_delete=models.CASCADE,
        related_name='games'
    )
    name = models.CharField(max_length=255)
    game_uid = models.CharField(max_length=255)
    image = models.ImageField(upload_to='games/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    min_bet = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    max_bet = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'

    def __str__(self):
        return f"{self.name} ({self.provider.code})"


# --- 10. GameLog ---

class GameLog(models.Model):
    """
    Game play log. Win amounts above user exposure_limit go partly to main_balance
    and remainder to exposure_balance; each leg has its own transaction (Exposure Logic #2).
    Bonus balance used only when main is 0 or below min_bet (Bonus Logic #2).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='game_logs'
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='game_logs'
    )
    provider = models.ForeignKey(
        GameProvider,
        on_delete=models.CASCADE,
        related_name='game_logs'
    )
    wallet = models.CharField(
        max_length=20,
        choices=GameLogWallet.choices
    )
    type = models.CharField(max_length=10, choices=GameLogType.choices)
    round = models.CharField(max_length=255, blank=True)
    match = models.CharField(max_length=255, blank=True)
    bet_amount = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    win_amount = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    lose_amount = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    before_balance = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    after_balance = models.DecimalField(max_digits=16, decimal_places=2, default=default_decimal_zero)
    provider_raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Game Log'
        verbose_name_plural = 'Game Logs'

    def __str__(self):
        return f"{self.user} - {self.game} - {self.get_type_display()} ({self.created_at})"


# --- 11. Transaction ---

class Transaction(models.Model):
    """
    Transaction log. Per Transaction Logic: a single action (e.g. deposit approved)
    may create two transactions (one for master balance out, one for user balance in).
    Filter by user for display so player sees only their transactions.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    action_type = models.CharField(max_length=10, choices=TransactionActionType.choices)
    wallet = models.CharField(max_length=20, choices=TransactionWallet.choices)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions_from'
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions_to'
    )
    balance_before = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True
    )
    balance_after = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return f"{self.user} - {self.get_transaction_type_display()} - {self.amount} ({self.status})"


# --- 12. ActivityLog ---

class ActivityLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    device = models.CharField(max_length=255, blank=True)
    game = models.ForeignKey(
        Game,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=30, choices=ActivityAction.choices)
    action_date = models.DateField(null=True, blank=True)
    action_time = models.TimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} ({self.created_at})"


# --- 13. Message ---

class Message(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages_sent'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages_received'
    )
    message = models.TextField()
    file = models.FileField(upload_to='message_files/', blank=True, null=True)
    image = models.ImageField(upload_to='message_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.created_at})"


# --- 14. Testimonial ---

class Testimonial(models.Model):
    """'from' in PDF stored as testimonial_from to avoid Python reserved keyword."""
    image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    name = models.CharField(max_length=255)
    testimonial_from = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    stars = models.PositiveSmallIntegerField(default=5)
    game_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'

    def __str__(self):
        return f"{self.name} - {self.stars} stars"


# --- 15. CMSPage ---

class CMSPage(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    image = models.ImageField(upload_to='cms/', blank=True, null=True)
    content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_header = models.BooleanField(default=False)
    is_footer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'CMS Page'
        verbose_name_plural = 'CMS Pages'

    def __str__(self):
        return self.title


# --- 16. SiteSetting ---

class SiteSetting(models.Model):
    name = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    phones = models.JSONField(default=list, blank=True)
    emails = models.JSONField(default=list, blank=True)
    whatsapp_number = models.CharField(max_length=50, blank=True)
    hero_title = models.CharField(max_length=500, blank=True)
    hero_subtitle = models.CharField(max_length=500, blank=True)
    active_players = models.PositiveIntegerField(default=0)
    games_available = models.PositiveIntegerField(default=0)
    total_winnings = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=default_decimal_zero
    )
    instant_payouts = models.PositiveIntegerField(default=0)
    footer_description = models.TextField(blank=True)
    home_stats = models.JSONField(default=list, blank=True)
    biggest_wins = models.JSONField(default=list, blank=True)
    promo_banners = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Setting'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.name or f"SiteSetting (id={self.pk})"


# --- 17. PasswordResetOTP (for forgot-password flow) ---

class PasswordResetOTP(models.Model):
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='password_reset_otps')
    otp = models.CharField(max_length=10)
    channel = models.CharField(max_length=10)  # 'phone' or 'email'
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for user {self.user_id} ({self.channel})"
