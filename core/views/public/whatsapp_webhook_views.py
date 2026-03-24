"""
Meta WhatsApp Cloud API webhooks: GET (verify) + POST (delivery status).
Callback URL: https://<domain>/webhook/whatsapp/
"""
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from core.models import PasswordResetOTP, SignupOTP, SuperSetting

logger = logging.getLogger(__name__)


def _get_verify_token() -> str:
    ss = SuperSetting.get_settings()
    if ss and (ss.wa_webhook_verify_token or "").strip():
        return (ss.wa_webhook_verify_token or "").strip()
    return (getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or "").strip()


def _apply_status_updates(waba_message_id: str, status_val: str) -> None:
    if not waba_message_id or not status_val:
        return
    status_val = status_val.strip()[:32]
    SignupOTP.objects.filter(waba_message_id=waba_message_id).update(whatsapp_delivery_status=status_val)
    PasswordResetOTP.objects.filter(waba_message_id=waba_message_id).update(whatsapp_delivery_status=status_val)


@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def whatsapp_webhook(request: Request):
    if request.method == "GET":
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        expected = _get_verify_token()
        if (
            mode == "subscribe"
            and challenge
            and expected
            and token
            and constant_time_compare(expected, token)
        ):
            return HttpResponse(challenge, content_type="text/plain", status=200)
        logger.warning("WhatsApp webhook GET verify failed mode=%s", mode)
        return HttpResponse("Forbidden", status=403)

    # POST — always 200 for Meta
    try:
        data = request.data
        if isinstance(data, dict):
            for entry in data.get("entry") or []:
                if not isinstance(entry, dict):
                    continue
                for change in entry.get("changes") or []:
                    if not isinstance(change, dict):
                        continue
                    value = change.get("value") or {}
                    if not isinstance(value, dict):
                        continue
                    for st in value.get("statuses") or []:
                        if not isinstance(st, dict):
                            continue
                        mid = (st.get("id") or "").strip()
                        status_val = (st.get("status") or "").strip()
                        if mid:
                            _apply_status_updates(mid, status_val)
    except Exception:
        logger.exception("WhatsApp webhook POST parse error")

    return HttpResponse("OK", content_type="text/plain", status=200)
