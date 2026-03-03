"""Reports for super: Total D/W, Super Master D/W, Super D/W State."""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count
from core.permissions import require_role, get_masters_queryset, get_players_queryset
from core.models import Deposit, Withdraw, User, UserRole


def _date_filter(qs, date_from, date_to, date_field="created_at"):
    if date_from:
        qs = qs.filter(**{f"{date_field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{date_field}__date__lte": date_to})
    return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def total_dw_list(request):
    """Per-user deposit/withdrawal totals (super: masters + players). date_from, date_to."""
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    masters = get_masters_queryset(request.user)
    players = get_players_queryset(request.user)
    results = []
    for user in list(masters) + list(players):
        dep_qs = _date_filter(
            Deposit.objects.filter(user=user, status="approved"),
            date_from, date_to
        )
        wd_qs = _date_filter(
            Withdraw.objects.filter(user=user, status="approved"),
            date_from, date_to
        )
        total_dep = dep_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total_wd = wd_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total = total_dep - total_wd
        results.append({
            "username": user.username,
            "user_id": user.id,
            "deposit": str(total_dep),
            "withdrawal": str(total_wd),
            "total": str(total),
        })
    return Response(results)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def super_master_dw_list(request):
    """One row per master: no_of_withdrawal, withdrawal, no_of_deposit, deposit, total. date_from, date_to."""
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    masters = get_masters_queryset(request.user)
    results = []
    for master in masters:
        dep_qs = _date_filter(
            Deposit.objects.filter(user__parent=master, status="approved"),
            date_from, date_to
        )
        wd_qs = _date_filter(
            Withdraw.objects.filter(user__parent=master, status="approved"),
            date_from, date_to
        )
        no_dep = dep_qs.count()
        no_wd = wd_qs.count()
        total_dep = dep_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total_wd = wd_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total = total_dep - total_wd
        results.append({
            "username": master.username,
            "user_id": master.id,
            "no_of_deposit": no_dep,
            "deposit": str(total_dep),
            "no_of_withdrawal": no_wd,
            "withdrawal": str(total_wd),
            "total": str(total),
        })
    return Response(results)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def super_dw_state_list(request):
    """One row per user (masters + players): no_of_deposit, total_deposit, no_of_withdrawal, total_withdrawal, net_d_w, total_d_w."""
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    masters = get_masters_queryset(request.user)
    players = get_players_queryset(request.user)
    results = []
    for user in list(masters) + list(players):
        dep_qs = _date_filter(
            Deposit.objects.filter(user=user, status="approved"),
            date_from, date_to
        )
        wd_qs = _date_filter(
            Withdraw.objects.filter(user=user, status="approved"),
            date_from, date_to
        )
        no_dep = dep_qs.count()
        no_wd = wd_qs.count()
        total_dep = dep_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        total_wd = wd_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        net_d_w = total_dep - total_wd
        total_d_w = total_dep + total_wd
        results.append({
            "username": user.username,
            "user_id": user.id,
            "no_of_deposit": no_dep,
            "total_deposit": str(total_dep),
            "no_of_withdrawal": no_wd,
            "total_withdrawal": str(total_wd),
            "net_d_w": str(net_d_w),
            "total_d_w": str(total_d_w),
        })
    return Response(results)
