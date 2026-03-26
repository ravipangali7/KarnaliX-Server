from rest_framework.throttling import SimpleRateThrottle


class PerIpRateThrottle(SimpleRateThrottle):
    """
    Simple IP-based throttle helper.

    Uses X-Forwarded-For first (when behind a reverse proxy), otherwise falls
    back to REMOTE_ADDR.
    """

    def get_ident(self, request):
        xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
        if xff:
            # XFF can contain a chain: client, proxy1, proxy2...
            return xff.split(",")[0].strip() or "unknown"
        return request.META.get("REMOTE_ADDR") or "unknown"


class LoginIPThrottle(PerIpRateThrottle):
    scope = "login"


class RegisterIPThrottle(PerIpRateThrottle):
    scope = "register"


class GoogleLoginIPThrottle(PerIpRateThrottle):
    scope = "google_login"


class GoogleCompleteIPThrottle(PerIpRateThrottle):
    scope = "google_complete"


class SignupCheckPhoneIPThrottle(PerIpRateThrottle):
    scope = "signup_check_phone"


class SignupSendOtpIPThrottle(PerIpRateThrottle):
    scope = "signup_send_otp"


class SignupVerifyOtpIPThrottle(PerIpRateThrottle):
    scope = "signup_verify_otp"


class ForgotPasswordSearchIPThrottle(PerIpRateThrottle):
    scope = "forgot_password_search"


class ForgotPasswordSendOtpIPThrottle(PerIpRateThrottle):
    scope = "forgot_password_send_otp"


class ForgotPasswordVerifyResetIPThrottle(PerIpRateThrottle):
    scope = "forgot_password_verify_reset"


class ForgotPasswordWhatsappContactIPThrottle(PerIpRateThrottle):
    scope = "forgot_password_whatsapp_contact"

