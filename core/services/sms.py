"""
SMS service for KarnaliX.
Stub implementation: all send functions are placeholders with no real API calls.
Wire a real provider (e.g. Twilio, AWS SNS) when ready.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Minimum length for a valid phone (digits only); adjust per region
MIN_PHONE_DIGITS = 10
MAX_PHONE_DIGITS = 15


def validate_phone(phone: str) -> bool:
    """
    Basic phone validation (length/format).
    Returns True if phone looks valid for sending SMS.
    """
    if not phone or not isinstance(phone, str):
        return False
    digits = re.sub(r"\D", "", phone)
    return MIN_PHONE_DIGITS <= len(digits) <= MAX_PHONE_DIGITS


def send_otp(phone: str, code: str) -> bool:
    """
    Send OTP code to phone via SMS.
    Stub: no real API call; log only. Return True so backend can proceed.
    """
    # TODO: Integrate real SMS provider API here
    logger.info("SMS send_otp stub: phone=%s code=%s", phone, code)
    return True


def send_sms(phone: str, message: str) -> bool:
    """
    Send arbitrary SMS message to phone.
    Stub: no real API call; log only. Return True so callers can proceed.
    """
    # TODO: Integrate real SMS provider API here
    logger.info("SMS send_sms stub: phone=%s message_len=%d", phone, len(message))
    return True
