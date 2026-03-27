"""Powerhouse Analytics: overview, game, finance, customer-behaviour, and per-user analytics."""
from datetime import timedelta, datetime
from decimal import Decimal

from django.db.models import Sum, Count, Avg, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import (
    User, UserRole,
    GameLog, GameLogType,
    Transaction, TransactionType,
    Deposit, Withdraw,
    ActivityLog, ActivityAction,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date_range(request, default_days=30):
    today = timezone.now().date()
    raw_from = request.query_params.get("date_from", "").strip()
    raw_to = request.query_params.get("date_to", "").strip()
    try:
        date_from = datetime.strptime(raw_from, "%Y-%m-%d").date() if raw_from else today - timedelta(days=default_days)
        date_to = datetime.strptime(raw_to, "%Y-%m-%d").date() if raw_to else today
    except (ValueError, TypeError):
        date_from = today - timedelta(days=default_days)
        date_to = today
    return date_from, date_to


def _date_series(date_from, date_to):
    """Yield each calendar date between date_from and date_to inclusive."""
    cur = date_from
    while cur <= date_to:
        yield cur
        cur += timedelta(days=1)


# ── 1. Overview ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _parse_date_range(request)

    # Total players / new registrations in range
    total_players = User.objects.filter(role=UserRole.PLAYER).count()
    new_players = User.objects.filter(
        role=UserRole.PLAYER,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).count()

    # Active users (placed a bet or logged in during range)
    active_users = (
        ActivityLog.objects
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .exclude(user__isnull=True)
        .values("user_id")
        .distinct()
        .count()
    )

    # GameLog aggregates for period
    gl_qs = GameLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        user__role=UserRole.PLAYER,
    )
    gl_agg = gl_qs.aggregate(
        total_bets=Count("id"),
        total_bet_amount=Sum("bet_amount"),
        total_win_amount=Sum("win_amount"),
        total_lose_amount=Sum("lose_amount"),
    )
    total_bet_amount = gl_agg["total_bet_amount"] or Decimal("0")
    total_win_amount = gl_agg["total_win_amount"] or Decimal("0")
    platform_pl = total_bet_amount - total_win_amount

    # Deposits / withdrawals (approved) in range
    dep_agg = Deposit.objects.filter(
        status="approved",
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).aggregate(total=Sum("amount"), count=Count("id"))
    wd_agg = Withdraw.objects.filter(
        status="approved",
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).aggregate(total=Sum("amount"), count=Count("id"))
    total_deposits = dep_agg["total"] or Decimal("0")
    total_withdrawals = wd_agg["total"] or Decimal("0")
    revenue = total_deposits - total_withdrawals

    # Daily series for charts (deposits, withdrawals, bets, P/L)
    daily = []
    for d in _date_series(date_from, date_to):
        dep_day = Deposit.objects.filter(status="approved", created_at__date=d)
        wd_day = Withdraw.objects.filter(status="approved", created_at__date=d)
        gl_day = GameLog.objects.filter(created_at__date=d, user__role=UserRole.PLAYER)
        dep_sum = dep_day.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        wd_sum = wd_day.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        bet_agg = gl_day.aggregate(bet=Sum("bet_amount"), win=Sum("win_amount"))
        bet_sum = bet_agg["bet"] or Decimal("0")
        win_sum = bet_agg["win"] or Decimal("0")
        daily.append({
            "date": d.isoformat(),
            "deposits": str(dep_sum),
            "withdrawals": str(wd_sum),
            "bets": str(bet_sum),
            "platform_pl": str(bet_sum - win_sum),
            "new_players": User.objects.filter(role=UserRole.PLAYER, created_at__date=d).count(),
        })

    return Response({
        "summary": {
            "total_players": total_players,
            "new_players": new_players,
            "active_users": active_users,
            "total_bets": gl_agg["total_bets"] or 0,
            "total_bet_amount": str(total_bet_amount),
            "total_win_amount": str(total_win_amount),
            "platform_pl": str(platform_pl),
            "total_deposits": str(total_deposits),
            "deposits_count": dep_agg["count"] or 0,
            "total_withdrawals": str(total_withdrawals),
            "withdrawals_count": wd_agg["count"] or 0,
            "revenue": str(revenue),
        },
        "daily": daily,
    })


# ── 2. Game Analytics ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _parse_date_range(request)

    base_qs = GameLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        user__role=UserRole.PLAYER,
    )

    # Top 15 games by bet volume
    top_games = (
        base_qs
        .values("game__id", "game__name", "game__image_url", "provider__name")
        .annotate(
            bet_count=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
            lose_amount=Sum("lose_amount"),
            unique_players=Count("user_id", distinct=True),
        )
        .order_by("-bet_amount")[:15]
    )
    top_games_list = [
        {
            "game_id": r["game__id"],
            "game_name": r["game__name"] or "Unknown",
            "provider": r["provider__name"] or "Unknown",
            "game_image": r["game__image_url"] or "",
            "bet_count": r["bet_count"],
            "bet_amount": str(r["bet_amount"] or 0),
            "win_amount": str(r["win_amount"] or 0),
            "platform_pl": str((r["bet_amount"] or Decimal("0")) - (r["win_amount"] or Decimal("0"))),
            "unique_players": r["unique_players"],
        }
        for r in top_games
    ]

    # Provider breakdown
    providers = (
        base_qs
        .values("provider__id", "provider__name")
        .annotate(
            bet_count=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        .order_by("-bet_amount")
    )
    provider_list = [
        {
            "provider_id": r["provider__id"],
            "provider_name": r["provider__name"] or "Unknown",
            "bet_count": r["bet_count"],
            "bet_amount": str(r["bet_amount"] or 0),
            "platform_pl": str((r["bet_amount"] or Decimal("0")) - (r["win_amount"] or Decimal("0"))),
        }
        for r in providers
    ]

    # Category breakdown
    categories = (
        base_qs
        .values("game__category__id", "game__category__name")
        .annotate(
            bet_count=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        .order_by("-bet_amount")
    )
    category_list = [
        {
            "category_id": r["game__category__id"],
            "category_name": r["game__category__name"] or "Uncategorised",
            "bet_count": r["bet_count"],
            "bet_amount": str(r["bet_amount"] or 0),
            "platform_pl": str((r["bet_amount"] or Decimal("0")) - (r["win_amount"] or Decimal("0"))),
        }
        for r in categories
    ]

    # Daily game volume series
    daily = []
    for d in _date_series(date_from, date_to):
        agg = base_qs.filter(created_at__date=d).aggregate(
            bets=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        bet = agg["bet_amount"] or Decimal("0")
        win = agg["win_amount"] or Decimal("0")
        daily.append({
            "date": d.isoformat(),
            "bets": agg["bets"] or 0,
            "bet_amount": str(bet),
            "platform_pl": str(bet - win),
        })

    return Response({
        "top_games": top_games_list,
        "providers": provider_list,
        "categories": category_list,
        "daily": daily,
    })


# ── 3. Finance & P/L Analytics ────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def finance_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _parse_date_range(request)

    dep_base = Deposit.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    wd_base = Withdraw.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    # Summary
    dep_agg = dep_base.filter(status="approved").aggregate(total=Sum("amount"), count=Count("id"))
    wd_agg = wd_base.filter(status="approved").aggregate(total=Sum("amount"), count=Count("id"))
    total_deposits = dep_agg["total"] or Decimal("0")
    total_withdrawals = wd_agg["total"] or Decimal("0")

    # Bonus usage
    bonus_tx = Transaction.objects.filter(
        transaction_type=TransactionType.BONUS,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).aggregate(total=Sum("amount"), count=Count("id"))

    # Top 10 depositors
    top_depositors = (
        dep_base.filter(status="approved")
        .values("user__id", "user__username", "user__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:10]
    )
    top_depositors_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"] or "",
            "name": r["user__name"] or "",
            "total": str(r["total"] or 0),
            "count": r["count"],
        }
        for r in top_depositors
    ]

    # Top 10 withdrawers
    top_withdrawers = (
        wd_base.filter(status="approved")
        .values("user__id", "user__username", "user__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:10]
    )
    top_withdrawers_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"] or "",
            "name": r["user__name"] or "",
            "total": str(r["total"] or 0),
            "count": r["count"],
        }
        for r in top_withdrawers
    ]

    # P/L from GameLog
    gl_agg = GameLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        user__role=UserRole.PLAYER,
    ).aggregate(bet=Sum("bet_amount"), win=Sum("win_amount"))
    platform_pl = (gl_agg["bet"] or Decimal("0")) - (gl_agg["win"] or Decimal("0"))

    # Daily series
    daily = []
    running_pl = Decimal("0")
    for d in _date_series(date_from, date_to):
        dep_d = dep_base.filter(status="approved", created_at__date=d).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        wd_d = wd_base.filter(status="approved", created_at__date=d).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        gl_d = GameLog.objects.filter(created_at__date=d, user__role=UserRole.PLAYER).aggregate(
            bet=Sum("bet_amount"), win=Sum("win_amount")
        )
        day_pl = (gl_d["bet"] or Decimal("0")) - (gl_d["win"] or Decimal("0"))
        running_pl += day_pl
        daily.append({
            "date": d.isoformat(),
            "deposits": str(dep_d),
            "withdrawals": str(wd_d),
            "net": str(dep_d - wd_d),
            "platform_pl": str(day_pl),
            "running_pl": str(running_pl),
        })

    return Response({
        "summary": {
            "total_deposits": str(total_deposits),
            "deposits_count": dep_agg["count"] or 0,
            "total_withdrawals": str(total_withdrawals),
            "withdrawals_count": wd_agg["count"] or 0,
            "net_cash": str(total_deposits - total_withdrawals),
            "platform_pl": str(platform_pl),
            "bonus_given": str(bonus_tx["total"] or 0),
            "bonus_count": bonus_tx["count"] or 0,
        },
        "top_depositors": top_depositors_list,
        "top_withdrawers": top_withdrawers_list,
        "daily": daily,
    })


# ── 4. Customer Behaviour Analytics ──────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_analytics(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    date_from, date_to = _parse_date_range(request)

    activity_base = ActivityLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        user__role=UserRole.PLAYER,
    )

    # Daily active users and login counts
    daily = []
    for d in _date_series(date_from, date_to):
        day_act = activity_base.filter(created_at__date=d)
        dau = day_act.exclude(user__isnull=True).values("user_id").distinct().count()
        logins = day_act.filter(action=ActivityAction.LOGIN).count()
        new_reg = User.objects.filter(role=UserRole.PLAYER, created_at__date=d).count()
        daily.append({
            "date": d.isoformat(),
            "active_users": dau,
            "logins": logins,
            "new_registrations": new_reg,
        })

    # Device breakdown
    devices = (
        activity_base
        .exclude(device="")
        .values("device")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    device_list = [{"device": r["device"], "count": r["count"]} for r in devices]

    # Top players by bet volume
    gl_base = GameLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        user__role=UserRole.PLAYER,
    )
    top_bettors = (
        gl_base
        .values("user__id", "user__username", "user__name")
        .annotate(
            bet_count=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        .order_by("-bet_amount")[:10]
    )
    top_bettors_list = [
        {
            "user_id": r["user__id"],
            "username": r["user__username"] or "",
            "name": r["user__name"] or "",
            "bet_count": r["bet_count"],
            "bet_amount": str(r["bet_amount"] or 0),
            "win_amount": str(r["win_amount"] or 0),
            "platform_pl": str((r["bet_amount"] or Decimal("0")) - (r["win_amount"] or Decimal("0"))),
        }
        for r in top_bettors
    ]

    # Action distribution
    action_counts = (
        activity_base
        .values("action")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    action_list = [{"action": r["action"], "count": r["count"]} for r in action_counts]

    # Summary metrics
    total_logins = activity_base.filter(action=ActivityAction.LOGIN).count()
    unique_active = activity_base.exclude(user__isnull=True).values("user_id").distinct().count()

    return Response({
        "summary": {
            "unique_active_users": unique_active,
            "total_logins": total_logins,
        },
        "daily": daily,
        "top_bettors": top_bettors_list,
        "devices": device_list,
        "action_distribution": action_list,
    })


# ── 5. Per-User Analytics ─────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_analytics(request, user_id):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    try:
        player = User.objects.get(pk=user_id, role=UserRole.PLAYER)
    except User.DoesNotExist:
        return Response({"detail": "Player not found."}, status=404)

    date_from, date_to = _parse_date_range(request)

    # GameLog summary for this user
    gl_qs = GameLog.objects.filter(
        user=player,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    gl_agg = gl_qs.aggregate(
        total_bets=Count("id"),
        total_bet_amount=Sum("bet_amount"),
        total_win_amount=Sum("win_amount"),
        total_lose_amount=Sum("lose_amount"),
    )

    # Top games for this player
    top_games = (
        gl_qs
        .values("game__id", "game__name", "provider__name")
        .annotate(
            bet_count=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        .order_by("-bet_amount")[:8]
    )
    top_games_list = [
        {
            "game_id": r["game__id"],
            "game_name": r["game__name"] or "Unknown",
            "provider": r["provider__name"] or "Unknown",
            "bet_count": r["bet_count"],
            "bet_amount": str(r["bet_amount"] or 0),
            "win_amount": str(r["win_amount"] or 0),
        }
        for r in top_games
    ]

    # Deposit / withdraw history for this user in range
    deposits = list(
        Deposit.objects.filter(user=player, created_at__date__gte=date_from, created_at__date__lte=date_to)
        .order_by("-created_at")
        .values("id", "amount", "status", "created_at")[:50]
    )
    withdrawals = list(
        Withdraw.objects.filter(user=player, created_at__date__gte=date_from, created_at__date__lte=date_to)
        .order_by("-created_at")
        .values("id", "amount", "status", "created_at")[:50]
    )

    # Recent activity
    activities = list(
        ActivityLog.objects.filter(user=player, created_at__date__gte=date_from, created_at__date__lte=date_to)
        .order_by("-created_at")
        .values("action", "device", "ip", "remarks", "created_at")[:50]
    )

    # Daily bet trend for this player
    daily = []
    for d in _date_series(date_from, date_to):
        agg = gl_qs.filter(created_at__date=d).aggregate(
            bets=Count("id"),
            bet_amount=Sum("bet_amount"),
            win_amount=Sum("win_amount"),
        )
        bet = agg["bet_amount"] or Decimal("0")
        win = agg["win_amount"] or Decimal("0")
        daily.append({
            "date": d.isoformat(),
            "bets": agg["bets"] or 0,
            "bet_amount": str(bet),
            "win_amount": str(win),
            "pl": str(bet - win),
        })

    dep_agg = Deposit.objects.filter(user=player, status="approved").aggregate(total=Sum("amount"))
    wd_agg = Withdraw.objects.filter(user=player, status="approved").aggregate(total=Sum("amount"))

    return Response({
        "user": {
            "id": player.pk,
            "username": player.username,
            "name": player.name,
            "phone": player.phone,
            "main_balance": str(player.main_balance or 0),
            "bonus_balance": str(player.bonus_balance or 0),
            "pl_balance": str(player.pl_balance or 0),
            "joined": player.created_at.isoformat() if player.created_at else None,
            "all_time_deposits": str(dep_agg["total"] or 0),
            "all_time_withdrawals": str(wd_agg["total"] or 0),
        },
        "summary": {
            "total_bets": gl_agg["total_bets"] or 0,
            "total_bet_amount": str(gl_agg["total_bet_amount"] or 0),
            "total_win_amount": str(gl_agg["total_win_amount"] or 0),
            "total_lose_amount": str(gl_agg["total_lose_amount"] or 0),
            "platform_pl": str(
                (gl_agg["total_bet_amount"] or Decimal("0")) - (gl_agg["total_win_amount"] or Decimal("0"))
            ),
        },
        "top_games": top_games_list,
        "deposits": [
            {**d, "amount": str(d["amount"]), "created_at": d["created_at"].isoformat() if d["created_at"] else None}
            for d in deposits
        ],
        "withdrawals": [
            {**w, "amount": str(w["amount"]), "created_at": w["created_at"].isoformat() if w["created_at"] else None}
            for w in withdrawals
        ],
        "activities": [
            {**a, "created_at": a["created_at"].isoformat() if a["created_at"] else None}
            for a in activities
        ],
        "daily": daily,
    })
