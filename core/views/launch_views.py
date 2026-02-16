"""Game launch: build provider URL and redirect authenticated user."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import SuperSetting, UserRole
from core.game_api_client import launch_game


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def launch_game_redirect(request):
    """
    GET ?game_uid=... - Redirect to provider launch URL.
    Requires authenticated player. Uses SuperSetting for base_url, secret, token, domain_url.
    """
    err = require_role(request, [UserRole.PLAYER])
    if err:
        return err
    game_uid = request.GET.get("game_uid") or request.query_params.get("game_uid")
    if not game_uid or not game_uid.strip():
        return Response(
            {"detail": "game_uid is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    game_uid = game_uid.strip()
    settings = SuperSetting.get_settings()
    if not settings or not settings.game_api_url or not settings.game_api_secret or not settings.game_api_token:
        return Response(
            {"detail": "Game API not configured (game_api_url, secret, token)."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    user = request.user
    wallet_amount = float((user.main_balance or 0) + (user.bonus_balance or 0))
    user_id = user.username
    domain_url = (settings.game_api_domain_url or "").strip() or None
    try:
        r = launch_game(
            base_url=settings.game_api_url.rstrip("/"),
            secret_key=settings.game_api_secret,
            token=settings.game_api_token,
            user_id=user_id,
            wallet_amount=wallet_amount,
            game_uid=game_uid,
            domain_url=domain_url,
            allow_redirects=False,
        )
    except Exception as e:
        return Response(
            {"detail": f"Launch failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(r.headers["Location"])
    return Response(
        {"detail": "Provider did not redirect.", "status": r.status_code, "body": r.text[:500]},
        status=status.HTTP_502_BAD_GATEWAY,
    )
