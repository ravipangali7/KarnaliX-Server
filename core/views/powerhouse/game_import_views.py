"""Powerhouse: Direct import of providers/games from external game API."""
import logging
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import require_role
from core.models import SuperSetting, GameProvider, GameCategory, Game, UserRole
from core.game_api_client import get_providers, get_provider_games

logger = logging.getLogger(__name__)


def _get_base_url():
    settings = SuperSetting.get_settings()
    if not settings or not settings.game_api_url or not settings.game_api_url.strip():
        return None
    return settings.game_api_url.strip()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_providers_list(request):
    """GET list of providers from external game API (getProvider). Powerhouse only."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    base_url = _get_base_url()
    if not base_url:
        return Response(
            {"detail": "Game API URL not set. Configure it in Super Settings."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        providers = get_providers(base_url)
    except Exception as e:
        logger.exception("Import providers: external API failed")
        return Response(
            {"detail": f"External API error: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(providers)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_provider_games(request, provider_code):
    """GET categories and games for a provider from external API (providerGame). Powerhouse only."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    base_url = _get_base_url()
    if not base_url:
        return Response(
            {"detail": "Game API URL not set. Configure it in Super Settings."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        games = get_provider_games(base_url, provider_code, count=1000)
    except Exception as e:
        logger.exception("Import provider games: external API failed")
        return Response(
            {"detail": f"External API error: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    categories = sorted({(g.get("game_type") or "").strip() or "Other" for g in games if g})
    result = {
        "categories": categories,
        "games": [
            {
                "game_uid": (g.get("game_code") or "").strip(),
                "game_name": (g.get("game_name") or "").strip(),
                "game_type": (g.get("game_type") or "").strip() or "Other",
                "game_image": (g.get("game_image") or "").strip() or "",
            }
            for g in games
            if (g.get("game_code") or "").strip()
        ],
    }
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_games_create(request):
    """POST import selected games: get_or_create provider/categories, create games (skip existing). Powerhouse only."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    data = request.data or {}
    provider_code = (data.get("provider_code") or "").strip()
    provider_name = (data.get("provider_name") or "").strip() or provider_code
    games = data.get("games")
    if not provider_code:
        return Response(
            {"detail": "provider_code is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(games, list):
        return Response(
            {"detail": "games must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    provider, provider_created = GameProvider.objects.get_or_create(
        code=provider_code,
        defaults={"name": provider_name, "is_active": True},
    )
    if not provider_created and provider.name != provider_name:
        provider.name = provider_name
        provider.save(update_fields=["name"])

    categories_created = 0
    games_created = 0
    games_skipped = 0
    default_category_name = "Other"

    for g in games:
        if not isinstance(g, dict):
            continue
        game_uid = (g.get("game_uid") or g.get("game_code") or "").strip()
        if not game_uid:
            continue
        game_name = (g.get("game_name") or "").strip() or game_uid
        game_type = (g.get("game_type") or "").strip() or default_category_name
        game_image = (g.get("game_image") or "").strip() or None
        cat_name = game_type[:255] if game_type else default_category_name

        cat, cat_created = GameCategory.objects.get_or_create(
            name=cat_name,
            defaults={"is_active": True},
        )
        if cat_created:
            categories_created += 1

        _, created = Game.objects.get_or_create(
            provider=provider,
            game_uid=game_uid,
            defaults={
                "name": game_name[:255],
                "category": cat,
                "image_url": game_image,
                "is_active": True,
                "min_bet": Decimal("0"),
                "max_bet": Decimal("0"),
            },
        )
        if created:
            games_created += 1
        else:
            games_skipped += 1

    return Response({
        "provider_created": provider_created,
        "categories_created": categories_created,
        "games_created": games_created,
        "games_skipped": games_skipped,
    })
