"""
WhatsApp OTP: Meta Cloud API (Graph) using SuperSetting credentials, with Flexgrew fallback.
"""
import re
import traceback
from urllib.parse import urlunparse, urlparse

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
    """Full detail for ops: stdout (gunicorn journal)."""
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


def _extract_otp_digits(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", str(text or ""))
    return m.group(1) if m else None


def _settings_flexgrew_api_key() -> str:
    return (getattr(settings, "FLEXGREW_API_KEY", None) or "").strip()


def _settings_flexgrew_base_url() -> str:
    return (getattr(settings, "FLEXGREW_BASE_URL", None) or "").strip()


def _normalize_flexgrew_base_url(url: str) -> str:
    """
    Ensure host-only URLs use /api (Flexgrew docs: base https://flexgrew.cloud/api).
    e.g. https://flexgrew.cloud -> https://flexgrew.cloud/api
    """
    url = (url or "").strip().rstrip("/")
    if not url:
        return "https://flexgrew.cloud/api"
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url
    path = (p.path or "").strip("/")
    if not path:
        p2 = p._replace(path="/api", params="", query="", fragment="")
        return urlunparse(p2).rstrip("/")
    return url


FLEXGREW_HTML_BODY = (
    "Flexgrew returned the website (HTML) instead of the JSON API. "
    "Confirm the base URL is https://flexgrew.cloud/api (or your provider's API root) "
    "and that the API is reachable from this server."
)


def _flexgrew_response_looks_like_html(r: requests.Response) -> bool:
    ct = (r.headers.get("Content-Type") or "").lower()
    if "text/html" in ct:
        return True
    raw = (r.text or "").lstrip()[:500]
    low = raw.lower()
    return low.startswith("<!doctype") or low.startswith("<html")


def _flexgrew_public_error(r: requests.Response, fj: dict | None) -> str:
    if _flexgrew_response_looks_like_html(r):
        return FLEXGREW_HTML_BODY
    return (
        _flexgrew_error_message(fj) or (r.text or "")[:400] or f"HTTP {r.status_code}"
    )[:500]


def _log_flexgrew_bad_response(where: str, r: requests.Response | None, exc: BaseException | None = None) -> None:
    if r is not None and _flexgrew_response_looks_like_html(r):
        print(
            f"[whatsapp_service] {where} status={r.status_code} url={getattr(r, 'url', '')} body=<HTML omitted>",
            flush=True,
        )
        if exc is not None:
            print(f"[whatsapp_service] exc={exc!r}\n{traceback.format_exc()}", flush=True)
        return
    _log_bad_whatsapp_response(where, r, exc)


def _resolve_flexgrew_config(ss: SuperSetting | None) -> tuple[str, str]:
    """API key and base URL: SuperSetting first, then Django settings."""
    key = ""
    base = ""
    if ss:
        key = (ss.flexgrew_api_key or "").strip()
        base = (ss.flexgrew_base_url or "").strip()
    if not key:
        key = _settings_flexgrew_api_key()
    if not base:
        base = _settings_flexgrew_base_url()
    if not base:
        base = "https://flexgrew.cloud/api"
    base = _normalize_flexgrew_base_url(base)
    return key, base.rstrip("/")


def _flexgrew_template_id_as_int(ss: SuperSetting | None) -> int | None:
    """Parse Flexgrew template id from stored string; API expects integer templateId."""
    if not ss:
        return None
    raw = (getattr(ss, "flexgrew_otp_template_id", None) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _flexgrew_error_message(fj: dict | None) -> str:
    if not fj:
        return ""
    msg = fj.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    err = fj.get("error")
    if isinstance(err, str) and err.strip():
        return err.strip()
    sc = fj.get("statusCode")
    if sc is not None:
        return f"Error {sc}"
    return ""


def _verify_meta_access_token(token: str, phone_number_id: str, api_version: str) -> tuple[bool, str]:
    """
    Pre-flight: confirm the Bearer token can access this WhatsApp phone number ID on Graph API.
    """
    ver = (api_version or "v22.0").strip().lstrip("/") or "v22.0"
    pid = phone_number_id.strip()
    url = f"https://graph.facebook.com/{ver}/{pid}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, params={"fields": "id,display_phone_number"}, timeout=15)
        if r.status_code == 200:
            return True, ""
        data = _safe_response_json(r)
        if data and isinstance(data.get("error"), dict):
            err = data["error"]
            msg = err.get("message") or "Token check failed"
            code = err.get("code")
            if code is not None:
                msg = f"{msg} (code {code})"
        else:
            msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        print(f"[whatsapp_service] Meta token pre-check failed: status={r.status_code}", flush=True)
        return False, (
            "WhatsApp access token invalid or expired, or phone number ID is wrong. "
            f"Regenerate the token in Meta (WhatsApp → API Setup). Details: {msg[:200]}"
        )
    except requests.RequestException as e:
        print(f"[whatsapp_service] Meta token pre-check request error: {str(e)[:200]}", flush=True)
        return False, getattr(e, "message", str(e)) or "Network error during token check"


def _send_via_meta(
    to_digits: str,
    text: str,
    token: str,
    phone_number_id: str,
    api_version: str,
    template_name: str,
    template_language: str,
    body_param: bool,
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
    if name_lower in META_TEMPLATES_NO_BODY_PARAMS:
        body_param = False

    template: dict = {
        "name": name,
        "language": {"code": lang},
    }
    if body_param:
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


def _send_via_flexgrew(to_digits: str, text: str, ss: SuperSetting | None = None) -> tuple[bool, str, None]:
    api_key, base_url = _resolve_flexgrew_config(ss)
    if not api_key:
        print(
            "[whatsapp_service] WhatsApp OTP not sent: Flexgrew API key not set (SuperSetting or FLEXGREW_API_KEY).",
            flush=True,
        )
        return False, "WhatsApp OTP not configured", None

    phone_e164 = "+" + to_digits
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    template_id = _flexgrew_template_id_as_int(ss)

    try:
        contact_id = None
        r = requests.get(
            f"{base_url}/contacts",
            params={"search": phone_e164, "limit": 10},
            headers=headers,
            timeout=15,
        )
        if r.status_code in (401, 403):
            fj = _safe_response_json(r)
            err = _flexgrew_public_error(r, fj)
            print(f"[whatsapp_service] Flexgrew GET /contacts auth failed: {err[:200]}", flush=True)
            return False, err, None
        if r.status_code != 200 and _flexgrew_response_looks_like_html(r):
            print(
                "[whatsapp_service] Flexgrew GET /contacts returned HTML (wrong base URL or API routing)",
                flush=True,
            )
            return False, FLEXGREW_HTML_BODY, None
        if r.status_code == 200:
            data = _safe_response_json(r)
            if data is None:
                _log_flexgrew_bad_response("Flexgrew GET /contacts 200 non-JSON", r)
                return False, "WhatsApp provider returned invalid response (not JSON)", None
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
                err = _flexgrew_public_error(r, fj)
                _log_flexgrew_bad_response("Flexgrew POST /contacts error", r)
                print(f"[whatsapp_service] Flexgrew create contact failed: {err[:200]}", flush=True)
                return False, err or "Failed to create contact", None
            created = _safe_response_json(r)
            if not created:
                _log_flexgrew_bad_response("Flexgrew POST /contacts 200 empty or non-JSON", r)
                return False, "WhatsApp provider returned invalid response (not JSON)", None
            contact_id = created.get("id")
            if not contact_id:
                return False, "Invalid contact response", None

        try:
            cid = int(contact_id)
        except (TypeError, ValueError):
            return False, "Invalid contact id from Flexgrew", None

        r = requests.post(
            f"{base_url}/chats/start",
            headers=headers,
            json={"contactId": cid},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            fj = _safe_response_json(r)
            err = _flexgrew_public_error(r, fj)
            _log_flexgrew_bad_response("Flexgrew POST /chats/start error", r)
            print(f"[whatsapp_service] Flexgrew start chat failed: {err[:200]}", flush=True)
            return False, err or "Failed to start chat", None
        start_data = _safe_response_json(r)
        if not start_data:
            _log_flexgrew_bad_response("Flexgrew POST /chats/start 200 empty or non-JSON", r)
            return False, "WhatsApp provider returned invalid response (not JSON)", None
        chat_uuid = start_data.get("uuid")
        if not chat_uuid:
            return False, "Invalid chat response", None

        if template_id is not None:
            otp = _extract_otp_digits(text)
            if not otp:
                return False, "Could not extract 6-digit OTP for Flexgrew template", None
            payload = {"templateId": template_id, "variables": {"1": otp}}
            r = requests.post(
                f"{base_url}/chats/{chat_uuid}/template",
                headers=headers,
                json=payload,
                timeout=20,
            )
        else:
            r = requests.post(
                f"{base_url}/chats/{chat_uuid}/messages",
                headers=headers,
                json={"message": text, "type": "text"},
                timeout=15,
            )
        if r.status_code not in (200, 201):
            fj = _safe_response_json(r)
            err = _flexgrew_public_error(r, fj)
            _log_flexgrew_bad_response("Flexgrew send (template or message) error", r)
            print(f"[whatsapp_service] Flexgrew send failed: {err[:200]}", flush=True)
            return False, err or "Failed to send message", None

        return True, "Sent", None
    except requests.RequestException as e:
        _log_flexgrew_bad_response("Flexgrew HTTP error", getattr(e, "response", None), e)
        print(f"[whatsapp_service] WhatsApp OTP request error: {str(e)[:200]}", flush=True)
        return False, getattr(e, "message", str(e)) or "Network error", None


def meta_settings_deliver_otp_in_message(ss: SuperSetting | None) -> bool:
    """
    True if Meta is configured to include the 6-digit OTP in the WhatsApp message.
    When False (e.g. hello_world or body param off), use SMS fallback on sites that allow SMS,
    or block with 503 on WhatsApp-only sites.
    Flexgrew-only setups (no Meta token+phone id) are treated as delivering the full text.
    """
    if not ss:
        return True
    token = (ss.whatsapp_secret_key or "").strip()
    phone_id = (ss.whatsapp_phone_number_id or "").strip()
    if not (token and phone_id):
        return True
    name = (ss.whatsapp_otp_template_name or "").strip().lower()
    if name in META_TEMPLATES_NO_BODY_PARAMS:
        return False
    return bool(ss.whatsapp_otp_template_body_param)


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str, str | None]:
    """
    Send OTP-related message via WhatsApp.
    Prefers Meta Cloud API when SuperSetting has token + phone number id + template name.
    Falls back to Flexgrew when SuperSetting or FLEXGREW_API_KEY has a Flexgrew API key.
    to: digits with country code, e.g. 9779812345678.
    text: message body (used by Flexgrew; Meta template mode extracts 6-digit OTP when body param enabled).
    Returns (success: bool, message: str, waba_message_id or None).
    """
    to_digits = "".join(c for c in str(to) if c.isdigit())
    if not to_digits or len(to_digits) < 10:
        return False, "Invalid phone number", None

    ss = SuperSetting.get_settings()
    if ss:
        token = (ss.whatsapp_secret_key or "").strip()
        phone_id = (ss.whatsapp_phone_number_id or "").strip()
        if token and phone_id:
            api_ver = (ss.whatsapp_api_version or "v22.0").strip()
            ok_tok, tok_msg = _verify_meta_access_token(token, phone_id, api_ver)
            if not ok_tok:
                flex_key, _ = _resolve_flexgrew_config(ss)
                if flex_key:
                    print(
                        f"[whatsapp_service] Meta token check failed; sending OTP via Flexgrew. "
                        f"{(tok_msg or '')[:200]}",
                        flush=True,
                    )
                    return _send_via_flexgrew(to_digits, text, ss)
                return False, tok_msg, None
            return _send_via_meta(
                to_digits,
                text,
                token=token,
                phone_number_id=phone_id,
                api_version=api_ver,
                template_name=(ss.whatsapp_otp_template_name or "").strip(),
                template_language=(ss.whatsapp_otp_template_language or "en_US").strip(),
                body_param=bool(ss.whatsapp_otp_template_body_param),
            )

    return _send_via_flexgrew(to_digits, text, ss)
