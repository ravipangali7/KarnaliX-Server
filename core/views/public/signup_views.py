"""
Signup flow: check phone, send OTP via SMS, verify OTP, then register (handled in auth_views).
"""
import random
import string
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import User, SignupOTP, SignupSession, SuperSetting
from core.services.sms_service import send_sms
from core.services.whatsapp_service import meta_settings_deliver_otp_in_message, send_whatsapp_otp
from core.utils.otp_host_policy import should_use_whatsapp_instead_of_sms


def normalize_phone(phone: str) -> str:
    """Normalize to digits only; if 10 digits starting with 9, assume Nepal and prepend 977."""
    digits = "".join(c for c in str(phone).strip() if c.isdigit())
    if len(digits) == 10 and digits.startswith("9"):
        return "977" + digits
    if len(digits) == 11 and digits.startswith("977"):
        return digits
    return digits if digits else ""


# Rate limit: 1 send per 60 seconds per phone
SIGNUP_OTP_COOLDOWN_SECONDS = 60


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_check_phone(request):
    """
    POST { "phone": "9779812345678" or "9812345678" }.
    Return { "exists": true } if user with that phone exists, else { "exists": false }.
    """
    phone = (request.data.get("phone") or "").strip()
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return Response({"detail": "Invalid phone number."}, status=status.HTTP_400_BAD_REQUEST)
    exists = User.objects.filter(phone=normalized).exists()
    return Response({"exists": exists})


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_send_otp(request):
    """
    POST { "phone": "...", "channel": "sms" | "whatsapp" }.
    channel defaults to "sms". Rate-limited. Create SignupOTP, send via chosen channel, return { "detail": "OTP sent." }.
    """
    phone = (request.data.get("phone") or "").strip()
    channel = (request.data.get("channel") or "sms").strip().lower()
    if channel not in ("sms", "whatsapp"):
        channel = "sms"
    if channel == "sms" and should_use_whatsapp_instead_of_sms(request):
        channel = "whatsapp"
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return Response({"detail": "Invalid phone number."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(phone=normalized).exists():
        return Response({"detail": "User already exists with this phone."}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    recent = SignupOTP.objects.filter(phone=normalized, created_at__gte=now - timedelta(seconds=SIGNUP_OTP_COOLDOWN_SECONDS)).first()
    if recent:
        return Response(
            {"detail": f"Please wait {SIGNUP_OTP_COOLDOWN_SECONDS} seconds before requesting another OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    delivery = channel
    if channel == "whatsapp":
        ss = SuperSetting.get_settings()
        if not meta_settings_deliver_otp_in_message(ss):
            tmpl = (ss.wa_template_name or "").strip() if ss else ""
            if should_use_whatsapp_instead_of_sms(request):
                print(
                    "[signup_send_otp] WhatsApp-only host: Meta template cannot include OTP in message "
                    f"(wa_template_name={tmpl!r}). Returning 503.",
                    flush=True,
                )
                return Response(
                    {
                        "detail": (
                            "This site sends codes only by WhatsApp, but the configured Meta template cannot include the "
                            "verification code (e.g. hello_world has no code field). In Powerhouse → Super Settings, "
                            "set template name to an approved template whose body has one variable for the 6-digit code."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            print(
                "[signup_send_otp] WhatsApp requested but Meta template cannot include OTP in message "
                f"(wa_template_name={tmpl!r}); falling back to SMS.",
                flush=True,
            )
            delivery = "sms"

    SignupOTP.objects.filter(phone=normalized).delete()
    otp = "".join(random.choices(string.digits, k=6))
    expires_at = now + timedelta(minutes=10)
    signup_otp = SignupOTP.objects.create(phone=normalized, otp=otp, expires_at=expires_at)

    text = f"Your LuckyUser365 verification code: {otp}"
    waba_id = None
    if delivery == "whatsapp":
        ok, msg, waba_id = send_whatsapp_otp(normalized, text)
    else:
        ok, msg = send_sms(normalized, text)
    if not ok:
        if channel == "whatsapp" and "not configured" in (msg or "").lower():
            if should_use_whatsapp_instead_of_sms(request):
                return Response({"detail": msg or "WhatsApp OTP is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            return Response({"detail": msg or "WhatsApp OTP not configured. Try SMS."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": msg or "Failed to send OTP."}, status=status.HTTP_502_BAD_GATEWAY)
    if ok and delivery == "whatsapp":
        upd: dict = {"whatsapp_delivery_status": "sent"}
        if waba_id:
            upd["waba_message_id"] = waba_id
        SignupOTP.objects.filter(pk=signup_otp.pk).update(**upd)
    detail = "OTP sent."
    if channel == "whatsapp" and delivery == "sms":
        detail = (
            "Your code was sent by text message (SMS). WhatsApp is connected but the template cannot include the "
            "code yet—ask your admin to set an authentication-style template in Super Settings."
        )
    return Response({"detail": detail, "delivery": delivery})


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_verify_otp(request):
    """
    POST { "phone": "...", "otp": "123456" }.
    If valid, delete OTP, create SignupSession, return { "signup_token": "..." }.
    """
    phone = (request.data.get("phone") or "").strip()
    otp = (request.data.get("otp") or "").strip()
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return Response({"detail": "Invalid phone number."}, status=status.HTTP_400_BAD_REQUEST)
    if not otp or len(otp) != 6:
        return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

    record = (
        SignupOTP.objects.filter(phone=normalized, otp=otp)
        .filter(expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if not record:
        return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

    SignupOTP.objects.filter(phone=normalized).delete()
    token = "".join(random.choices(string.ascii_letters + string.digits, k=48))
    expires_at = timezone.now() + timedelta(minutes=15)
    SignupSession.objects.create(phone=normalized, token=token, expires_at=expires_at)
    return Response({"signup_token": token})
