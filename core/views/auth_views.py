"""
Authentication views for KarnaliX.
Function-based views for login, register, me, logout, refresh token.
OTP send/verify for phone-first signup.
"""
import random
import string
from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from core.models import User, UserActivityLog
from core.services.sms import send_otp as sms_send_otp, validate_phone as sms_validate_phone

OTP_CACHE_KEY_PREFIX = "otp:"
VERIFIED_PHONE_CACHE_KEY_PREFIX = "verified_phone:"
OTP_TTL_SECONDS = 300  # 5 minutes
VERIFIED_PHONE_TTL_SECONDS = 300  # 5 minutes
OTP_LENGTH = 6


def get_tokens_for_user(user):
    """Generate JWT tokens for user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access_token': str(refresh.access_token),
    }


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def log_activity(user, action, request):
    """Log user activity."""
    UserActivityLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
    )


def _generate_otp(length=OTP_LENGTH):
    """Generate a numeric OTP string."""
    return "".join(random.choices(string.digits, k=length))


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp_view(request):
    """
    Send OTP to phone. Body: { "phone": "+977..." }.
    Stores OTP in cache and calls SMS service (stub).
    """
    phone = (request.data.get("phone") or "").strip()
    if not phone:
        return Response(
            {"detail": "Phone number is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not sms_validate_phone(phone):
        return Response(
            {"detail": "Invalid phone number"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = _generate_otp()
    cache_key = f"{OTP_CACHE_KEY_PREFIX}{phone}"
    cache.set(cache_key, {"code": code}, timeout=OTP_TTL_SECONDS)
    sms_send_otp(phone, code)
    return Response({"success": True})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_view(request):
    """
    Verify OTP for phone. Body: { "phone": "...", "otp": "123456" }.
    On success, sets verified_phone in cache for use in register.
    """
    phone = (request.data.get("phone") or "").strip()
    otp = (request.data.get("otp") or "").strip()
    if not phone or not otp:
        return Response(
            {"detail": "Phone and OTP are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    cache_key = f"{OTP_CACHE_KEY_PREFIX}{phone}"
    stored = cache.get(cache_key)
    if not stored or stored.get("code") != otp:
        return Response(
            {"detail": "Invalid or expired OTP"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    verified_key = f"{VERIFIED_PHONE_CACHE_KEY_PREFIX}{phone}"
    cache.set(verified_key, True, timeout=VERIFIED_PHONE_TTL_SECONDS)
    return Response({"success": True})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.
    Accepts email/username and password.
    Returns JWT tokens and user data.
    """
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Try to find user by email or username
    try:
        if '@' in email:
            user = User.objects.get(email=email)
        else:
            user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check password
    if not user.check_password(password):
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if user is active
    if user.status != 'ACTIVE':
        return Response(
            {'error': f'Account is {user.status.lower()}'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Update last login
    user.last_login_at = timezone.now()
    user.save(update_fields=['last_login_at'])
    
    # Log activity
    log_activity(user, 'LOGIN', request)
    
    # Generate tokens
    tokens = get_tokens_for_user(user)
    
    return Response({
        **tokens,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'phone': user.phone,
            'wallet_balance': str(user.wallet_balance),
            'exposure_balance': str(user.exposure_balance),
            'status': user.status,
            'is_active': user.is_active,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint.
    Creates new USER role account.
    Supports two flows:
    - Phone-first: phone (must be verified via verify-otp), username, password. Email set to placeholder.
    - Legacy: username, email, password. Phone optional.
    """
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    phone = request.data.get('phone', '').strip()
    referral_code = request.data.get('referral_code', '').strip()

    # Phone-first flow: phone present and no email
    phone_first = bool(phone) and not email

    if phone_first:
        # Require verified phone
        verified_key = f"{VERIFIED_PHONE_CACHE_KEY_PREFIX}{phone}"
        if not cache.get(verified_key):
            return Response(
                {'error': 'Phone number must be verified first. Request an OTP and verify it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = f"{phone}@karnalix.local"  # placeholder; User model allows blank but we set a unique placeholder
    else:
        # Legacy: username, email, password required
        if not username or not email or not password:
            return Response(
                {'error': 'Username, email, and password are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if len(password) < 6:
        return Response(
            {'error': 'Password must be at least 6 characters'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check for existing user
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not phone_first and User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if phone_first and User.objects.filter(phone=phone).exists():
        return Response(
            {'error': 'This phone number is already registered'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find referrer if code provided
    referred_by = None
    parent = None
    if referral_code:
        try:
            referred_by = User.objects.get(username=referral_code)
            if referred_by.role in ['POWERHOUSE', 'SUPER', 'MASTER']:
                parent = referred_by
        except User.DoesNotExist:
            pass

    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        phone=phone,
        role='USER',
        referred_by=referred_by,
        parent=parent,
        status='ACTIVE',
    )
    from core.serializers.user_serializers import generate_pin
    if not user.pin:
        user.pin = generate_pin()
        user.save(update_fields=['pin'])

    # Log activity
    log_activity(user, 'LOGIN', request)

    # Generate tokens
    tokens = get_tokens_for_user(user)

    return Response({
        **tokens,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'phone': user.phone,
            'wallet_balance': str(user.wallet_balance),
            'status': user.status,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current authenticated user's data.
    """
    user = request.user
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'phone': user.phone,
        'wallet_balance': str(user.wallet_balance),
        'exposure_balance': str(user.exposure_balance),
        'status': user.status,
        'is_active': user.is_active,
        'last_login_at': user.last_login_at,
        'created_at': user.created_at,
        'parent': {
            'id': user.parent.id,
            'username': user.parent.username,
            'role': user.parent.role,
        } if user.parent else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint.
    Blacklists the refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Log activity
        log_activity(request.user, 'LOGOUT', request)
        
        return Response({'message': 'Successfully logged out'})
    except TokenError:
        return Response({'message': 'Token already blacklisted or invalid'})


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Refresh JWT access token using refresh token.
    """
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access_token': str(refresh.access_token),
            'refresh': str(refresh),
        })
    except TokenError as e:
        return Response(
            {'error': 'Invalid or expired refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Change user password.
    """
    user = request.user
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    
    if not old_password or not new_password:
        return Response(
            {'error': 'Old password and new password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(old_password):
        return Response(
            {'error': 'Old password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(new_password) < 6:
        return Response(
            {'error': 'New password must be at least 6 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(new_password)
    user.save()
    
    # Log activity
    log_activity(user, 'PASSWORD_CHANGED', request)
    
    return Response({'message': 'Password changed successfully'})
