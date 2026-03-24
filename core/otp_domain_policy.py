"""
OTP delivery policy by player site hostname (apex = SMS only; currency subdomains = email + WhatsApp).

Hostname is taken from X-Player-Host, then Origin, Referer, then Host — see player_hostname().
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from django.conf import settings

SMS_ONLY_HOSTS = frozenset({"luckyuser365.com", "www.luckyuser365.com"})

# Currency player sites: no SMS on register/forgot.
EMAIL_WHATSAPP_SUBDOMAINS = frozenset({"bht", "inr", "bdt", "myr", "aed", "aud"})

_LU365_SUBDOMAIN = re.compile(
    r"^(?P<sub>bht|inr|bdt|myr|aed|aud)\.luckyuser365\.com$", re.IGNORECASE
)


def normalize_hostname(value: str) -> str:
    if not value:
        return ""
    v = value.strip().lower()
    if "://" in v:
        parsed = urlparse(v)
        v = (parsed.hostname or "").lower()
    else:
        v = v.split("/")[0].split(":")[0].strip().lower()
    return v


def player_hostname(request) -> str:
    """
    Prefer X-Player-Host (set by SPA), then Origin, Referer, then request Host.
    """
    raw = (request.META.get("HTTP_X_PLAYER_HOST") or "").strip()
    if raw:
        return normalize_hostname(raw)

    origin = (request.META.get("HTTP_ORIGIN") or "").strip()
    if origin:
        host = normalize_hostname(origin)
        if host:
            return host

    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if referer:
        host = normalize_hostname(referer)
        if host:
            return host

    return normalize_hostname(request.get_host() or "")


def otp_policy(hostname: str) -> str:
    """
    Return 'sms_only' or 'email_whatsapp'.
    Unknown hosts use settings.OTP_DOMAIN_POLICY_DEFAULT.
    """
    default = getattr(settings, "OTP_DOMAIN_POLICY_DEFAULT", "email_whatsapp")
    if default not in ("sms_only", "email_whatsapp"):
        default = "email_whatsapp"

    h = normalize_hostname(hostname)
    if not h:
        return default

    if h in SMS_ONLY_HOSTS:
        return "sms_only"

    if _LU365_SUBDOMAIN.match(h):
        return "email_whatsapp"

    return default


def otp_policy_for_request(request) -> str:
    return otp_policy(player_hostname(request))


def forgot_channel_allowed(policy: str, channel: str) -> bool:
    """channel: phone | email | whatsapp. Apex: SMS (phone) + email for email-only accounts; no WhatsApp."""
    if policy == "sms_only":
        return channel in ("phone", "email")
    return channel in ("email", "whatsapp")


def signup_channel_allowed(policy: str, channel: str) -> bool:
    """channel: sms | whatsapp | email"""
    if policy == "sms_only":
        return channel == "sms"
    return channel in ("whatsapp", "email")
