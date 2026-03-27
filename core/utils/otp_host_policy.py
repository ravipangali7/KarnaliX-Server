"""OTP delivery rules by frontend hostname (Origin / Referer)."""
from urllib.parse import urlparse

# These player-site hosts never use SMS; OTP goes via WhatsApp when phone/SMS is requested.
NO_SMS_FRONTEND_HOSTNAMES = frozenset(
    {
        "bht.luckyuser365.com",
        "inr.luckyuser365.com",
        "bdt.luckyuser365.com",
        "myr.luckyuser365.com",
        "aed.luckyuser365.com",
        "aud.luckyuser365.com",
        "lucky365bht.com",
        "lucky365ind.com",
        "lucky365bhd.com",
    }
)


def frontend_hostname_from_request(request) -> str:
    """Hostname of the site the user is on (SPA), not necessarily the API Host header."""
    origin = (request.META.get("HTTP_ORIGIN") or "").strip()
    if origin:
        try:
            h = urlparse(origin).hostname
            if h:
                return h.lower()
        except ValueError:
            pass
    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if referer:
        try:
            h = urlparse(referer).hostname
            if h:
                return h.lower()
        except ValueError:
            pass
    host = request.get_host() or ""
    return host.split(":")[0].lower()


def should_use_whatsapp_instead_of_sms(request) -> bool:
    return frontend_hostname_from_request(request) in NO_SMS_FRONTEND_HOSTNAMES
