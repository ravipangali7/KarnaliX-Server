"""
WhatsApp OTP: Meta Cloud API (Graph) using SuperSetting credentials, with Flexgrew fallback.
"""
import logging
import re
import traceback

import requests
from django.conf import settings

from core.models import SuperSetting

logger = logging.getLogger(__name__)


def _safe_response_json(r: requests.Response) -> dict | None:
    """Parse JSON body; never raise. Empty or non-JSON bodies return None."""
    raw = (r.text or "").strip()
    if not raw:
        return None
    try:
        out = r.json()
        return out if isinstance(out, dict) else None
    except ValueError:
        # requests may raise JSONDecodeError (subclass of ValueError) on empty/non-JSON body
        return None


def _log_bad_whatsapp_response(where: str, r: requests.Response | None, exc: BaseException | None = None) -> None:
    """Full detail for ops: stdout (gunicorn journal) + logger."""
    parts = [f"[whatsapp_service] {where}"]
    if r is not None:
        parts.append(f"status={r.status_code} url={getattr(r, 'url', '')}")
        body = (r.text or "")[:4000]
        parts.append(f"body={body!r}")
    if exc is not None:
        parts.append(f"exc={exc!r}")
        parts.append(traceback.format_exc())
    line = "\n".join(parts)
    print(line, flush=True)
    logger.error("%s", line[:2000])


def _extract_otp_digits(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", str(text or ""))
    return m.group(1) if m else None


def _get_flexgrew_api_key() -> str:
    return (getattr(settings, "FLEXGREW_API_KEY", None) or "").strip()


def _send_via_meta(
    to_digits: str,
    text: str,
    token: str,
    phone_number_id: str,
    api_version: str,
    template_name: str,
    template_language: str,
    body_param: bool,
) -> tuple[bool, str]:
    ver = (api_version or "v22.0").strip().lstrip("/") or "v22.0"
    pid = phone_number_id.strip()
    url = f"https://graph.facebook.com/{ver}/{pid}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    lang = (template_language or "en_US").strip() or "en_US"
    name = (template_name or "").strip()
    if not name:
        return False, "WhatsApp OTP template name not configured"

    template: dict = {
        "name": name,
        "language": {"code": lang},
    }
    if body_param:
        otp = _extract_otp_digits(text)
        if not otp:
            return False, "Could not extract 6-digit OTP for WhatsApp template"
        template["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": otp}],
            }
        ]

    payload = {
        "messaging_product": "whatsapp",
        "to": to_digits,
        "type": "template",
        "template": template,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            return True, "Sent"
        data = _safe_response_json(r)
        if data and isinstance(data.get("error"), dict):
            err = data["error"]
            msg = err.get("message") or r.text or f"HTTP {r.status_code}"
            code = err.get("code")
            if code is not None:
                msg = f"{msg} (code {code})"
        else:
            msg = r.text[:500] if r.text else f"HTTP {r.status_code}"
            if not (r.text or "").strip():
                _log_bad_whatsapp_response("Meta non-200 empty body", r)
        logger.warning("Meta WhatsApp send failed: %s", msg[:300])
        return False, msg[:500] if msg else "Failed to send WhatsApp"
    except requests.RequestException as e:
        _log_bad_whatsapp_response("Meta HTTP error", getattr(e, "response", None), e)
        logger.warning("Meta WhatsApp request error: %s", str(e)[:200])
        return False, getattr(e, "message", str(e)) or "Network error"


def _send_via_flexgrew(to_digits: str, text: str) -> tuple[bool, str]:
    api_key = _get_flexgrew_api_key()
    if not api_key:
        logger.warning("WhatsApp OTP not sent: FLEXGREW_API_KEY not set in settings.")
        return False, "WhatsApp OTP not configured"

    phone_e164 = "+" + to_digits
    base_url = (getattr(settings, "FLEXGREW_BASE_URL", None) or "").rstrip("/") or "https://flexgrew.cloud/api"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        contact_id = None
        r = requests.get(
            f"{base_url}/contacts",
            params={"search": phone_e164, "limit": 10},
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            data = _safe_response_json(r)
            if data is None:
                _log_bad_whatsapp_response("Flexgrew GET /contacts 200 non-JSON", r)
                return False, "WhatsApp provider returned invalid response (not JSON)"
            for c in data.get("data") or []:
                if (c.get("phone") or "").replace(" ", "") == phone_e164:
                    contact_id = c.get("id")
                    break

        if contact_id is None:
            r = requests.post(
                f"{base_url}/contacts",
                headers=headers,
                json={"first_name": "User", "phone": phone_e164},
                timeout=15,
            )
            if r.status_code not in (200, 201):
                fj = _safe_response_json(r)
                err = (fj or {}).get("message") if fj else None
                err = err or r.text or f"HTTP {r.status_code}"
                _log_bad_whatsapp_response("Flexgrew POST /contacts error", r)
                logger.warning("Flexgrew create contact failed: %s", err[:200])
                return False, (err or "Failed to create contact")[:500]
            created = _safe_response_json(r)
            if not created:
                _log_bad_whatsapp_response("Flexgrew POST /contacts 200 empty or non-JSON", r)
                return False, "WhatsApp provider returned invalid response (not JSON)"
            contact_id = created.get("id")
            if not contact_id:
                return False, "Invalid contact response"

        r = requests.post(
            f"{base_url}/chats/start",
            headers=headers,
            json={"contactId": contact_id},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            fj = _safe_response_json(r)
            err = (fj or {}).get("message") if fj else None
            err = err or r.text or f"HTTP {r.status_code}"
            _log_bad_whatsapp_response("Flexgrew POST /chats/start error", r)
            logger.warning("Flexgrew start chat failed: %s", err[:200])
            return False, (err or "Failed to start chat")[:500]
        start_data = _safe_response_json(r)
        if not start_data:
            _log_bad_whatsapp_response("Flexgrew POST /chats/start 200 empty or non-JSON", r)
            return False, "WhatsApp provider returned invalid response (not JSON)"
        chat_uuid = start_data.get("uuid")
        if not chat_uuid:
            return False, "Invalid chat response"

        r = requests.post(
            f"{base_url}/chats/{chat_uuid}/messages",
            headers=headers,
            json={"message": text, "type": "text"},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            fj = _safe_response_json(r)
            err = (fj or {}).get("message") if fj else None
            err = err or r.text or f"HTTP {r.status_code}"
            _log_bad_whatsapp_response("Flexgrew POST messages error", r)
            logger.warning("Flexgrew send message failed: %s", err[:200])
            return False, (err or "Failed to send message")[:500]

        return True, "Sent"
    except requests.RequestException as e:
        _log_bad_whatsapp_response("Flexgrew HTTP error", getattr(e, "response", None), e)
        logger.warning("WhatsApp OTP request error: %s", str(e)[:200])
        return False, getattr(e, "message", str(e)) or "Network error"


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str]:
    """
    Send OTP-related message via WhatsApp.
    Prefers Meta Cloud API when SuperSetting has token + phone number id + template name.
    Falls back to Flexgrew when FLEXGREW_API_KEY is set.
    to: digits with country code, e.g. 9779812345678.
    text: message body (used by Flexgrew; Meta template mode extracts 6-digit OTP when body param enabled).
    Returns (success: bool, message: str).
    """
    to_digits = "".join(c for c in str(to) if c.isdigit())
    if not to_digits or len(to_digits) < 10:
        return False, "Invalid phone number"

    ss = SuperSetting.get_settings()
    if ss:
        token = (ss.whatsapp_secret_key or "").strip()
        phone_id = (ss.whatsapp_phone_number_id or "").strip()
        if token and phone_id:
            return _send_via_meta(
                to_digits,
                text,
                token=token,
                phone_number_id=phone_id,
                api_version=(ss.whatsapp_api_version or "v22.0").strip(),
                template_name=(ss.whatsapp_otp_template_name or "").strip(),
                template_language=(ss.whatsapp_otp_template_language or "en_US").strip(),
                body_param=bool(ss.whatsapp_otp_template_body_param),
            )

    return _send_via_flexgrew(to_digits, text)
