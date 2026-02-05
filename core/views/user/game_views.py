"""
User game launch view.
Builds provider launch URL with AES-256-ECB encrypted payload (aligned with launch_game.php).
"""
import json
import base64
import logging
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import Game
from core.permissions import user_required

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError:
    AES = None
    pad = None


def _aes256_encrypt_ecb(key: str, data: str) -> str:
    """AES-256-ECB encrypt and base64 encode (PHP openssl_encrypt compatible)."""
    if AES is None or pad is None:
        raise RuntimeError("pycryptodome is required for game launch. Run: pip install pycryptodome")
    # Key must be 32 bytes for AES-256
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"\0")
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    # PHP uses OPENSSL_RAW_DATA so no default PKCS7 in PHP - but openssl_encrypt does add PKCS7 padding
    padded = pad(data.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("ascii")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@user_required
def launch_game(request, game_id):
    """
    Return launch_url for the given game (authenticated user).
    Payload is built from user wallet, game provider_game_uid, and provider api_secret.
    """
    try:
        game = Game.objects.select_related("provider").get(id=game_id)
    except Game.DoesNotExist:
        return Response({"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

    if game.status != Game.Status.ACTIVE:
        return Response({"error": "Game is not available"}, status=status.HTTP_400_BAD_REQUEST)

    if not game.provider_game_uid:
        return Response({"error": "Game has no provider identifier"}, status=status.HTTP_400_BAD_REQUEST)

    provider = game.provider
    if provider.status != "ACTIVE" or not provider.api_endpoint:
        return Response({"error": "Game provider is not available"}, status=status.HTTP_400_BAD_REQUEST)

    api_secret = provider.api_secret or getattr(settings, "GAME_PROVIDER_API_SECRET", "")
    if not api_secret:
        return Response({"error": "Provider API secret not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user = request.user
    try:
        wallet_amount = float(user.wallet_balance or 0)
    except (TypeError, ValueError):
        wallet_amount = 0.0
    user_id = user.id
    # Token: provider-level api_token, or per-user provider_token, or user id
    token = provider.api_token or (user.settings or {}).get("provider_token") or str(user_id)

    timestamp = int(round(__import__("time").time() * 1000))
    domain_url = getattr(settings, "SITE_DOMAIN", "").rstrip("/") or request.build_absolute_uri("/").rstrip("/")
    wallet_int = int(wallet_amount) if wallet_amount == int(wallet_amount) else wallet_amount

    raw_payload = {
        "user_id": user_id,
        "wallet_amount": wallet_int,
        "game_uid": game.provider_game_uid,
        "token": token,
        "timestamp": timestamp,
        "domain_url": domain_url,
    }
    payload_json = json.dumps(raw_payload, separators=(",", ":"), ensure_ascii=False)

    try:
        encrypted_payload = _aes256_encrypt_ecb(api_secret, payload_json)
    except Exception as e:
        logger.exception("Game launch encryption failed: %s", e)
        return Response({"error": "Failed to build launch URL"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    params = {
        "user_id": user_id,
        "wallet_amount": wallet_int,
        "game_uid": game.provider_game_uid,
        "token": token,
        "timestamp": timestamp,
        "payload": encrypted_payload,
    }
    query = urlencode(params)
    base_url = provider.api_endpoint.rstrip("/")
    launch_url = f"{base_url}?{query}"

    return Response({"launch_url": launch_url})
