"""
Public auth: login, register. Authenticated: me (current user + balances).
"""
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from core.models import User, UserRole, SignupSession, SuperSetting
from core.serializers import (
    LoginSerializer,
    RegisterSerializer,
    MeSerializer,
)
from core.services.bonus_service import apply_welcome_bonus, apply_referral_bonus
from core.views.public.signup_views import normalize_phone


def get_default_master():
    """Return the default master user for new signups (no referral)."""
    settings = SuperSetting.get_settings()
    if settings and settings.default_master_id:
        return settings.default_master
    return User.objects.filter(role=UserRole.MASTER).first()


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """POST { username, password } -> { token, user }."""
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(
        request,
        username=ser.validated_data['username'],
        password=ser.validated_data['password'],
    )
    if not user:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        return Response(
            {'detail': 'User account is disabled.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    token, _ = Token.objects.get_or_create(user=user)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST { signup_token, phone, name, password, referral_code? }. Creates user after OTP verification."""
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data.copy()
    signup_token = (data.get('signup_token') or '').strip()
    phone_raw = (data.get('phone') or '').strip()
    normalized_phone = normalize_phone(phone_raw)
    if not normalized_phone or len(normalized_phone) < 10:
        return Response({'detail': 'Invalid phone number.'}, status=status.HTTP_400_BAD_REQUEST)

    session = (
        SignupSession.objects.filter(token=signup_token, phone=normalized_phone)
        .filter(expires_at__gt=timezone.now())
        .first()
    )
    if not session:
        return Response({'detail': 'Invalid or expired signup token.'}, status=status.HTTP_400_BAD_REQUEST)

    referral_code = (data.pop('referral_code', None) or '').strip()
    parent = None
    referred_by = None
    if referral_code:
        referrer = User.objects.filter(username=referral_code).first()
        if referrer and referrer.role == UserRole.PLAYER and referrer.parent_id:
            parent = referrer.parent
            referred_by = referrer
    if parent is None:
        parent = get_default_master()
    if not parent:
        return Response({'detail': 'No default master configured. Contact support.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    username = normalized_phone
    if User.objects.filter(username=username).exists():
        username = f"user_{normalized_phone}"
    name = (data.get('name') or '').strip() or username
    password = data['password']

    user = User(
        username=username,
        role=UserRole.PLAYER,
        name=name,
        phone=normalized_phone,
        email='',
        whatsapp_number='',
        parent=parent,
        referred_by=referred_by,
    )
    user.set_password(password)
    user.save()

    applied_welcome, _ = apply_welcome_bonus(user)
    if user.referred_by_id:
        apply_referral_bonus(user.referred_by, user)

    SignupSession.objects.filter(token=signup_token).delete()
    token = Token.objects.create(user=user)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
        'welcome_bonus_applied': applied_welcome,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """GET current user and header balances."""
    serializer = MeSerializer(request.user)
    return Response(serializer.data)
