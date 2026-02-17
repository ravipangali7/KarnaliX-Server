"""
Provider game callback: POST from provider with round result; update user balance, GameLog, master PL.
Accepts both application/x-www-form-urlencoded and application/json bodies.
"""
import json
from decimal import Decimal
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from core.models import (
    SuperSetting,
    User,
    UserRole,
    Game,
    GameProvider,
    GameCategory,
    GameLog,
    GameLogWallet,
    GameLogType,
    Transaction,
    TransactionActionType,
    TransactionWallet,
    TransactionType,
    TransactionStatus,
)


def _get_user_by_mobile(mobile):
    """Resolve User by mobile (user_id from provider): username or id."""
    if not mobile:
        return None
    mobile = str(mobile).strip()
    user = User.objects.filter(username=mobile).first()
    if user:
        return user
    try:
        pk = int(mobile)
        return User.objects.filter(pk=pk).first()
    except (ValueError, TypeError):
        pass
    return None


def _get_or_create_game_and_provider(game_uid):
    """Resolve Game by game_uid; if not found, create placeholder provider/game."""
    game = Game.objects.filter(game_uid=game_uid).select_related("provider", "category").first()
    if game:
        return game
    cat, _ = GameCategory.objects.get_or_create(
        name="Other",
        defaults={"is_active": True},
    )
    prov, _ = GameProvider.objects.get_or_create(
        code="callback_unknown",
        defaults={"name": "Unknown (Callback)", "is_active": True},
    )
    game = Game.objects.create(
        provider=prov,
        category=cat,
        name=game_uid[:255],
        game_uid=game_uid,
        is_active=True,
    )
    return game


def _get_callback_data(request):
    """
    Return a dict of callback fields from either JSON body or request.POST.
    Same field names: mobile, user_id, bet_amount, win_amount, game_uid, game_round,
    token, wallet_before, wallet_after, change, timestamp.
    """
    content_type = (request.content_type or "").strip().split(";")[0].lower()
    if content_type == "application/json":
        try:
            body = request.body.decode("utf-8") if request.body else "{}"
            return json.loads(body) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    # form-encoded or other: use POST
    return request.POST.dict() if hasattr(request.POST, "dict") else dict(request.POST)


@csrf_exempt
@require_http_methods(["POST"])
def game_callback(request):
    """
    POST from provider: mobile, bet_amount, win_amount, game_uid, game_round, token,
    wallet_before, wallet_after, change, timestamp, currency_code.
    Accepts form-encoded or application/json body.
    Update user balance to wallet_after, create/update GameLog, update master pl_balance.
    Return JSON {"status": "ok"}.
    """
    data = _get_callback_data(request)

    def _get(key, default=""):
        val = data.get(key, default)
        return val if val is not None else default

    try:
        mobile = _get("mobile") or _get("user_id")
        bet = Decimal(str(_get("bet_amount", "0")))
        win = Decimal(str(_get("win_amount", "0")))
        game_uid = (_get("game_uid") or "").strip()
        game_round = (_get("game_round") or "").strip()
        token = _get("token") or ""
        wallet_before = Decimal(str(_get("wallet_before", "0")))
        wallet_after = Decimal(str(_get("wallet_after", "0")))
        change = Decimal(str(_get("change", "0")))
        timestamp = _get("timestamp") or timezone.now().isoformat()
    except Exception:
        return JsonResponse({"error": "Invalid parameters"}, status=400)

    settings = SuperSetting.get_settings()
    if settings and getattr(settings, "game_api_token", None) and settings.game_api_token:
        if token != settings.game_api_token:
            return JsonResponse({"error": "Invalid token"}, status=403)

    user = _get_user_by_mobile(mobile)
    if not user:
        return JsonResponse({"error": "User not found"}, status=400)

    if not game_round:
        return JsonResponse({"error": "game_round required"}, status=400)

    game_uid = game_uid or "unknown"
    game = _get_or_create_game_and_provider(game_uid)

    result_win = win > 0
    log_type = GameLogType.WIN if result_win else GameLogType.LOSE
    net = win - bet

    existing = GameLog.objects.filter(user=user, round=game_round).first()
    if existing:
        existing.bet_amount = bet
        existing.win_amount = win
        existing.type = log_type
        existing.after_balance = wallet_after
        existing.provider_raw_data = data
        existing.save(update_fields=["bet_amount", "win_amount", "type", "after_balance", "provider_raw_data", "updated_at"])
        game_log = existing
    else:
        game_log = GameLog.objects.create(
            user=user,
            game=game,
            provider=game.provider,
            wallet=GameLogWallet.MAIN_BALANCE,
            type=log_type,
            round=game_round,
            bet_amount=bet,
            win_amount=win,
            lose_amount=bet - win if not result_win else Decimal("0"),
            before_balance=wallet_before,
            after_balance=wallet_after,
            provider_raw_data=data,
        )

    user.main_balance = wallet_after
    user.save(update_fields=["main_balance"])

    master = getattr(user, "parent", None)
    if master and master.role == UserRole.MASTER:
        master.pl_balance = (master.pl_balance or Decimal("0")) + (bet - win)
        master.save(update_fields=["pl_balance"])

    Transaction.objects.create(
        user=user,
        action_type=TransactionActionType.IN if net >= 0 else TransactionActionType.OUT,
        wallet=TransactionWallet.MAIN_BALANCE,
        transaction_type=TransactionType.PL,
        amount=abs(net),
        status=TransactionStatus.SUCCESS,
        remarks=f"Game round {game_round}",
    )

    return JsonResponse({"status": "ok"}, status=200)
