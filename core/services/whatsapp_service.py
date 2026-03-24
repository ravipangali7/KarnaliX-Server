"""
WhatsApp OTP: Meta Cloud API (Graph) using SuperSetting wa_* fields or WA_* env.
"""
import re
import traceback

import requests
from django.conf import settings

from core.models import SuperSetting

# Meta sample / fixed templates: no {{1}} body variables — never send template.components.
META_TEMPLATES_NO_BODY_PARAMS = frozenset(
    {
        "hello_world",
        "sample_shipping_confirmation",
        "sample_issue_resolution",
    }
)


def _safe_response_json(r: requests.Response) -> dict | None:
    raw = (r.text or "").strip()
    if not raw:
        return None
    try:
        out = r.json()
        return out if isinstance(out, dict) else None
    except ValueError:
        return None


def _log_bad_whatsapp_response(where: str, r: requests.Response | None, exc: BaseException | None = None) -> None:
    parts = [f"[whatsapp_service] {where}"]
    if r is not None:
        parts.append(f"status={r.status_code} url={getattr(r, 'url', '')}")
        body = (r.text or "")[:4000]
        parts.append(f"body={body!r}")
    if exc is not None:
        parts.append(f"exc={exc!r}")
        parts.append(traceback.format_exc())
    print("\n".join(parts), flush=True)


def _extract_otp_digits(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", str(text or ""))
    return m.group(1) if m else None


def _env_wa_access_token() -> str:
    return (getattr(settings, "WA_ACCESS_TOKEN", None) or "").strip()


def _env_wa_phone_number_id() -> str:
    return (getattr(settings, "WA_PHONE_NUMBER_ID", None) or "").strip()


def _env_wa_api_version() -> str:
    return (getattr(settings, "WA_API_VERSION", None) or "").strip()


def _resolve_wa_config(ss: SuperSetting | None) -> tuple[str, str, str, str, str]:
    """access_token, phone_number_id, api_version, template_name, template_language."""
    token = ""
    phone_id = ""
    api_ver = ""
    tmpl = ""
    lang = ""
    if ss:
        token = (ss.wa_access_token or "").strip()
        phone_id = (ss.wa_phone_number_id or "").strip()
        api_ver = (ss.wa_api_version or "v22.0").strip()
        tmpl = (ss.wa_template_name or "").strip()
        lang = (ss.wa_template_language or "en_US").strip()
    if not token:
        token = _env_wa_access_token()
    if not phone_id:
        phone_id = _env_wa_phone_number_id()
    if not api_ver:
        api_ver = _env_wa_api_version() or "v22.0"
    if not lang:
        lang = "en_US"
    return token, phone_id, api_ver, tmpl, lang


def _send_meta_template(
    to_digits: str,
    text: str,
    token: str,
    phone_number_id: str,
    api_version: str,
    template_name: str,
    template_language: str,
) -> tuple[bool, str, str | None]:
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
        return False, "WhatsApp OTP template name not configured", None

    name_lower = name.lower()
    use_body = name_lower not in META_TEMPLATES_NO_BODY_PARAMS

    template: dict = {
        "name": name,
        "language": {"code": lang},
    }
    if use_body:
        otp = _extract_otp_digits(text)
        if not otp:
            return False, "Could not extract 6-digit OTP for WhatsApp template", None
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
            data_ok = _safe_response_json(r)
            waba_id = None
            if data_ok:
                msgs = data_ok.get("messages")
                if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
                    waba_id = (msgs[0].get("id") or "").strip() or None
            return True, "Sent", waba_id
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
        print(f"[whatsapp_service] Meta WhatsApp send failed: {msg[:300]}", flush=True)
        return False, msg[:500] if msg else "Failed to send WhatsApp", None
    except requests.RequestException as e:
        _log_bad_whatsapp_response("Meta HTTP error", getattr(e, "response", None), e)
        print(f"[whatsapp_service] Meta WhatsApp request error: {str(e)[:200]}", flush=True)
        return False, getattr(e, "message", str(e)) or "Network error", None


def meta_settings_deliver_otp_in_message(ss: SuperSetting | None) -> bool:
    """
    True if the configured template can include the 6-digit OTP (body variable).
    False for hello_world and other Meta sample templates without {{1}}, or missing template name.
    """
    if not ss:
        return True
    name = (ss.wa_template_name or "").strip().lower()
    if not name:
        return False
    if name in META_TEMPLATES_NO_BODY_PARAMS:
        return False
    return True


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str, str | None]:
    """
    Send OTP-related message via Meta WhatsApp Cloud API template.
    to: digits with country code, e.g. 9779812345678.
    text: must contain a 6-digit code when template requires body variable.
    """
    to_digits = "".join(c for c in str(to) if c.isdigit())
    if not to_digits or len(to_digits) < 10:
        return False, "Invalid phone number", None

    ss = SuperSetting.get_settings()
    token, phone_id, api_ver, tmpl, lang = _resolve_wa_config(ss)
    if not token or not phone_id:
        print(
            "[whatsapp_service] WhatsApp OTP not sent: wa_access_token or wa_phone_number_id not set "
            "(SuperSetting or WA_ACCESS_TOKEN / WA_PHONE_NUMBER_ID).",
            flush=True,
        )
        return False, "WhatsApp OTP not configured", None

    return _send_meta_template(
        to_digits,
        text,
        token=token,
        phone_number_id=phone_id,
        api_version=api_ver,
        template_name=tmpl,
        template_language=lang,
    )
