"""Powerhouse-only: catalog + execute bulk data cleanup (see clean_data_service)."""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import UserRole
from core.services.clean_data_service import (
    DELETION_ORDER,
    PROTECTED_KEYS,
    execute_clean,
)

logger = logging.getLogger(__name__)

MODEL_LABELS = {
    "transaction": "Transactions",
    "game_log": "Bet history (game logs)",
    "activity_log": "Activity logs",
    "coming_soon_enrollment": "Coming soon enrollments",
    "deposit": "Deposits",
    "withdraw": "Withdrawals",
    "bonus_request": "Bonus requests",
    "message": "Messages",
    "payment_mode": "Payment modes",
    "password_reset_otp": "Password reset OTPs",
    "signup_otp": "Signup OTPs",
    "signup_session": "Signup sessions",
    "bonus_rule": "Bonus rules",
    "live_betting_event": "Live betting events",
    "live_betting_section": "Live betting sections",
    "slider_slide": "Slider slides",
    "popup": "Popups",
    "promotion": "Promotions",
    "coming_soon": "Coming soon (CMS)",
    "cms_page": "CMS pages",
    "testimonial": "Testimonials",
    "payment_method": "Payment methods (templates)",
    "country": "Countries",
    "user": "Users (Super / Master / Player only)",
    "super_setting": "Super settings (reset to defaults)",
    "site_setting": "Site settings (reset to defaults)",
}

PROTECTED_UI = [
    {"id": "game", "label": "Games", "helper": "Always preserved"},
    {"id": "game_category", "label": "Game categories", "helper": "Always preserved"},
    {"id": "game_provider", "label": "Game providers", "helper": "Always preserved"},
]

PRESET_USER = [
    "deposit",
    "withdraw",
    "transaction",
    "game_log",
    "bonus_request",
    "coming_soon_enrollment",
]
PRESET_MASTER = PRESET_USER + ["activity_log", "message", "payment_mode"]
PRESET_SUPER = PRESET_MASTER + [
    "bonus_rule",
    "coming_soon",
    "password_reset_otp",
    "signup_otp",
    "signup_session",
    "user",
]
PRESET_POWERHOUSE = PRESET_SUPER + [
    "slider_slide",
    "popup",
    "promotion",
    "cms_page",
    "testimonial",
    "payment_method",
    "country",
    "live_betting_event",
    "live_betting_section",
    "super_setting",
    "site_setting",
]

PRESETS = {
    "user": PRESET_USER,
    "master": PRESET_MASTER,
    "super": PRESET_SUPER,
    "powerhouse": PRESET_POWERHOUSE,
}


def _catalog_models():
    out = []
    for key in DELETION_ORDER:
        if key in PROTECTED_KEYS:
            continue
        out.append(
            {
                "id": key,
                "label": MODEL_LABELS.get(key, key),
                "protected": False,
            }
        )
    return out


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clean_data_catalog(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    return Response(
        {
            "models": _catalog_models(),
            "protected": PROTECTED_UI,
            "presets": PRESETS,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clean_data_execute(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err

    pin = (request.data.get("pin") or "").strip()
    password = request.data.get("password") or ""
    if not pin:
        return Response({"detail": "PIN is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({"detail": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.pin or request.user.pin != pin:
        return Response({"detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.check_password(password):
        return Response({"detail": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)

    raw_models = request.data.get("models")
    if not isinstance(raw_models, list):
        return Response({"detail": "models must be a list of string keys."}, status=status.HTTP_400_BAD_REQUEST)

    models_list = [str(m).strip() for m in raw_models if m is not None and str(m).strip()]
    models_list = [m for m in models_list if m not in PROTECTED_KEYS]

    allowed = {k for k in DELETION_ORDER}
    models_list = [m for m in models_list if m in allowed]

    if not models_list:
        return Response(
            {"detail": "Select at least one cleanable model (protected entries are ignored)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        deleted_counts = execute_clean(models_list, request.user.pk)
    except Exception:
        logger.exception("clean_data_execute failed user_id=%s", request.user.pk)
        return Response(
            {"detail": "Clean data failed. Check server logs."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"deleted_counts": deleted_counts})
