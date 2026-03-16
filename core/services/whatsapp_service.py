"""
Send OTP via WhatsApp using flexgrew.cloud API.
API key and base URL from Django settings: FLEXGREW_API_KEY, FLEXGREW_BASE_URL.
"""
import logging

import requests

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Return API key from settings (FLEXGREW_API_KEY)."""
    key = (getattr(settings, "FLEXGREW_API_KEY", None) or "").strip()
    return key


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str]:
    """
    Send OTP message to the given number via WhatsApp (flexgrew.cloud).
    to: full phone with country code (digits only), e.g. 9779812345678.
    text: message body (e.g. "Your KarnaliX verification code: 123456").
    Returns (success: bool, message: str).
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("WhatsApp OTP not sent: FLEXGREW_API_KEY not set in settings.")
        return False, "WhatsApp OTP not configured"

    to_digits = "".join(c for c in str(to) if c.isdigit())
    if not to_digits or len(to_digits) < 10:
        return False, "Invalid phone number"

    phone_e164 = "+" + to_digits
    base_url = (getattr(settings, "FLEXGREW_BASE_URL", None) or "").rstrip("/") or "https://flexgrew.cloud/api"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        # 1. Find or create contact
        contact_id = None
        r = requests.get(
            f"{base_url}/contacts",
            params={"search": phone_e164, "limit": 10},
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            for c in (data.get("data") or []):
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
                err = (r.json() or {}).get("message") or r.text or f"HTTP {r.status_code}"
                logger.warning("Flexgrew create contact failed: %s", err[:200])
                return False, err or "Failed to create contact"
            contact_id = r.json().get("id")
            if not contact_id:
                return False, "Invalid contact response"

        # 2. Start or get chat
        r = requests.post(
            f"{base_url}/chats/start",
            headers=headers,
            json={"contactId": contact_id},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            err = (r.json() or {}).get("message") or r.text or f"HTTP {r.status_code}"
            logger.warning("Flexgrew start chat failed: %s", err[:200])
            return False, err or "Failed to start chat"
        chat_uuid = (r.json() or {}).get("uuid")
        if not chat_uuid:
            return False, "Invalid chat response"

        # 3. Send message
        r = requests.post(
            f"{base_url}/chats/{chat_uuid}/messages",
            headers=headers,
            json={"message": text, "type": "text"},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            err = (r.json() or {}).get("message") or r.text or f"HTTP {r.status_code}"
            logger.warning("Flexgrew send message failed: %s", err[:200])
            return False, err or "Failed to send message"

        return True, "Sent"
    except requests.RequestException as e:
        logger.warning("WhatsApp OTP request error: %s", str(e)[:200])
        return False, getattr(e, "message", str(e)) or "Network error"
