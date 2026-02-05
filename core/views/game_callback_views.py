"""
Game provider callback view.
Accepts POST with bet/win data (aligned with callback.php) and updates wallet + logs.
"""
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import User, Game, GameProvider, GameTransactionLog, Bet, WalletTransaction


@api_view(["POST"])
@permission_classes([AllowAny])
def game_callback(request):
    """
    Provider callback: mobile (user id), bet_amount, win_amount, game_uid, game_round,
    token, wallet_before, wallet_after, change, timestamp.
    Updates user wallet to wallet_after and logs the transaction.
    """
    mobile = request.data.get("mobile") or request.POST.get("mobile")
    bet_amount = request.data.get("bet_amount") or request.POST.get("bet_amount", 0)
    win_amount = request.data.get("win_amount") or request.POST.get("win_amount", 0)
    game_uid = request.data.get("game_uid") or request.POST.get("game_uid")
    game_round = request.data.get("game_round") or request.POST.get("game_round", "")
    wallet_before = request.data.get("wallet_before") or request.POST.get("wallet_before", 0)
    wallet_after = request.data.get("wallet_after") or request.POST.get("wallet_after", 0)
    ts = request.data.get("timestamp") or request.POST.get("timestamp") or timezone.now().isoformat()

    if mobile is None or mobile == "":
        return Response({"error": "mobile required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=mobile)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        bet_amount = Decimal(str(bet_amount))
        win_amount = Decimal(str(win_amount))
        wallet_before = Decimal(str(wallet_before))
        wallet_after = Decimal(str(wallet_after))
    except (TypeError, ValueError):
        return Response({"error": "Invalid numeric fields"}, status=status.HTTP_400_BAD_REQUEST)

    # Resolve game by provider_game_uid (optional)
    game = None
    provider = None
    if game_uid:
        game = Game.objects.filter(provider_game_uid=game_uid).select_related("provider").first()
        if game:
            provider = game.provider

    # Update user wallet
    user.wallet_balance = wallet_after
    user.save(update_fields=["wallet_balance", "updated_at"])

    # Log wallet transaction
    WalletTransaction.objects.create(
        user=user,
        type=WalletTransaction.TransactionType.BET_SETTLED,
        amount=win_amount - bet_amount,
        balance_before=wallet_before,
        balance_after=wallet_after,
        reference_id=game_round or None,
        remarks=f"Game callback round {game_round}",
        created_by=user,
    )

    # GameTransactionLog
    if game and provider:
        GameTransactionLog.objects.create(
            user=user,
            game=game,
            provider=provider,
            provider_bet_id=game_round,
            transaction_type=GameTransactionLog.TransactionType.WIN if win_amount > 0 else GameTransactionLog.TransactionType.BET,
            round=game_round,
            bet_amount=bet_amount,
            win_amount=win_amount,
            before_balance=wallet_before,
            after_balance=wallet_after,
            status=GameTransactionLog.Status.COMPLETED,
            processed_at=timezone.now(),
        )

    # Bet: update or create by (user, game, provider_bet_id)
    if game:
        bet_result = Bet.Result.WON if win_amount > 0 else Bet.Result.LOST
        round_id = game_round or str(timezone.now().timestamp())
        bet, created = Bet.objects.update_or_create(
            user=user,
            game=game,
            provider_bet_id=round_id,
            defaults={
                "bet_amount": bet_amount,
                "win_amount": win_amount,
                "result": bet_result,
                "settled_at": timezone.now(),
            },
        )

    return Response({"status": "ok"})
