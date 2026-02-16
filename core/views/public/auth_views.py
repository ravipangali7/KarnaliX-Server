"""
Public auth: login, register. Authenticated: me (current user + balances).
"""
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from core.models import User, UserRole
from core.serializers import (
    LoginSerializer,
    RegisterSerializer,
    MeSerializer,
)
from core.services.bonus_service import apply_welcome_bonus


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
    """POST { username, password, name?, phone?, email?, whatsapp_number?, referral_code? }."""
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data.copy()
    referral_code = data.pop('referral_code', None) or ''
    parent = None
    referred_by = None
    if referral_code:
        referrer = User.objects.filter(username=referral_code.strip()).first()
        if referrer and referrer.role == UserRole.PLAYER and referrer.parent_id:
            parent = referrer.parent
            referred_by = referrer
    user = User(
        username=data['username'],
        role=UserRole.PLAYER,
        name=data.get('name') or '',
        phone=data.get('phone') or '',
        email=data.get('email') or '',
        whatsapp_number=data.get('whatsapp_number') or '',
        parent=parent,
        referred_by=referred_by,
    )
    user.set_password(data['password'])
    user.save()
    applied, msg = apply_welcome_bonus(user)
    token = Token.objects.create(user=user)
    serializer = MeSerializer(user)
    return Response({
        'token': token.key,
        'user': serializer.data,
        'welcome_bonus_applied': applied,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """GET current user and header balances."""
    serializer = MeSerializer(request.user)
    return Response(serializer.data)
