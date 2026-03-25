"""
Powerhouse-only bulk data cleanup. Deletes selected models in FK-safe order inside one transaction.

Protected (never deleted here): Game, GameCategory, GameProvider — ignored if sent.

SuperSetting / SiteSetting: delete all rows then recreate a single row with model defaults so code
that calls .first() or get_settings() still finds one instance.
"""
import logging
from decimal import Decimal

from django.db import transaction

from core.models import (
    ActivityLog,
    BonusRequest,
    BonusRule,
    CMSPage,
    ComingSoon,
    ComingSoonEnrollment,
    Country,
    Deposit,
    GameLog,
    LiveBettingEvent,
    LiveBettingSection,
    Message,
    PasswordResetOTP,
    PaymentMethod,
    PaymentMode,
    Popup,
    Promotion,
    SignupOTP,
    SignupSession,
    SiteSetting,
    SliderSlide,
    SuperSetting,
    Testimonial,
    Transaction,
    User,
    UserRole,
    Withdraw,
)

logger = logging.getLogger(__name__)

# Server-side ignore (defense in depth; also omitted from GET catalog).
PROTECTED_KEYS = frozenset({"game", "game_category", "game_provider"})

# Execution order: dependents before parents / PROTECT targets.
DELETION_ORDER = [
    "transaction",
    "game_log",
    "activity_log",
    "coming_soon_enrollment",
    "deposit",
    "withdraw",
    "bonus_request",
    "message",
    "payment_mode",
    "password_reset_otp",
    "signup_otp",
    "signup_session",
    "bonus_rule",
    "live_betting_event",
    "live_betting_section",
    "slider_slide",
    "popup",
    "promotion",
    "coming_soon",
    "cms_page",
    "testimonial",
    "payment_method",
    "country",
    "user",
    "super_setting",
    "site_setting",
]

_MODEL_DELETE_FUNCS = {
    "transaction": lambda: Transaction.objects.all().delete(),
    "game_log": lambda: GameLog.objects.all().delete(),
    "activity_log": lambda: ActivityLog.objects.all().delete(),
    "coming_soon_enrollment": lambda: ComingSoonEnrollment.objects.all().delete(),
    "deposit": lambda: Deposit.objects.all().delete(),
    "withdraw": lambda: Withdraw.objects.all().delete(),
    "bonus_request": lambda: BonusRequest.objects.all().delete(),
    "message": lambda: Message.objects.all().delete(),
    "payment_mode": lambda: PaymentMode.objects.all().delete(),
    "password_reset_otp": lambda: PasswordResetOTP.objects.all().delete(),
    "signup_otp": lambda: SignupOTP.objects.all().delete(),
    "signup_session": lambda: SignupSession.objects.all().delete(),
    "bonus_rule": lambda: BonusRule.objects.all().delete(),
    "live_betting_event": lambda: LiveBettingEvent.objects.all().delete(),
    "live_betting_section": lambda: LiveBettingSection.objects.all().delete(),
    "slider_slide": lambda: SliderSlide.objects.all().delete(),
    "popup": lambda: Popup.objects.all().delete(),
    "promotion": lambda: Promotion.objects.all().delete(),
    "coming_soon": lambda: ComingSoon.objects.all().delete(),
    "cms_page": lambda: CMSPage.objects.all().delete(),
    "testimonial": lambda: Testimonial.objects.all().delete(),
    "payment_method": lambda: PaymentMethod.objects.all().delete(),
    "country": lambda: Country.objects.all().delete(),
}


def _count_tuple(result):
    """Django delete() returns (total_deleted, per_model_dict)."""
    if isinstance(result, tuple) and result and isinstance(result[0], int):
        return result[0]
    return 0


def _delete_users_non_powerhouse() -> int:
    """Clear SuperSetting.default_master, then remove super/master/player users (deepest roles first)."""
    SuperSetting.objects.update(default_master=None)
    total = 0
    for role in (UserRole.PLAYER, UserRole.MASTER, UserRole.SUPER):
        n, _ = User.objects.filter(role=role).delete()
        total += n
    return total


def _reset_super_setting() -> int:
    SuperSetting.objects.all().delete()
    SuperSetting.objects.create()
    return 1


def _reset_site_setting() -> int:
    SiteSetting.objects.all().delete()
    SiteSetting.objects.create(
        name="",
        phones=[],
        emails=[],
        home_stats=[],
        biggest_wins=[],
        promo_banners=[],
        site_categories_json={},
        site_top_games_json={},
        site_providers_json={},
        site_categories_game_json={},
        site_popular_games_json={},
        site_refer_bonus_json={},
        site_payments_accepted_json={},
        site_footer_json={},
        site_welcome_deposit_json={},
        site_theme_json={},
        total_winnings=Decimal("0.00"),
    )
    return 1


def execute_clean(selected_keys: list[str], powerhouse_user_id: int) -> dict[str, int]:
    """
    Run deletions for allowed keys in DELETION_ORDER. Ignores PROTECTED_KEYS.
    Preserves User with role POWERHOUSE (and Game / GameCategory / GameProvider rows).
    """
    allowed = {k for k in DELETION_ORDER}
    keys_set = {k for k in selected_keys if isinstance(k, str) and k in allowed}
    keys_set -= PROTECTED_KEYS

    sorted_keys = [k for k in DELETION_ORDER if k in keys_set]
    deleted_counts: dict[str, int] = {}

    with transaction.atomic():
        for key in sorted_keys:
            if key == "user":
                n = _delete_users_non_powerhouse()
                deleted_counts[key] = n
            elif key == "super_setting":
                deleted_counts[key] = _reset_super_setting()
            elif key == "site_setting":
                deleted_counts[key] = _reset_site_setting()
            else:
                fn = _MODEL_DELETE_FUNCS.get(key)
                if fn:
                    r = fn()
                    deleted_counts[key] = _count_tuple(r)

    logger.info(
        "clean_data executed user_id=%s models=%s counts=%s",
        powerhouse_user_id,
        sorted_keys,
        deleted_counts,
    )
    return deleted_counts
