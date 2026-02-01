"""
API views for games, categories, providers, promo banners, auth, and all core operations.
"""
import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import transaction as db_transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token

from .models import (
    Category, Provider, Game, PromoBanner, User, Wallet, UserSettings,
    Transaction, DepositRequest, WithdrawalRequest, Bet, Ticket, TicketMessage,
    PaymentMethod, SystemConfig, Bonus, FavoriteGame, Referral, Testimonial, ReferralTier,
)
from .serializers import (
    CategorySerializer,
    ProviderSerializer,
    GameSerializer,
    PromoBannerSerializer,
    UserSerializer,
    WalletSerializer,
    TransactionSerializer,
    DepositRequestSerializer,
    WithdrawalRequestSerializer,
    BetSerializer,
    TicketSerializer,
    TicketMessageSerializer,
    PaymentMethodSerializer,
    SystemConfigSerializer,
    BonusSerializer,
)


def _user_payload(user):
    """Return user dict for API (matches frontend AuthContext)."""
    return {
        "id": str(user.pk),
        "email": user.email or "",
        "username": user.username or "",
        "full_name": getattr(user, "name", None) or user.get_full_name() or "",
        "role": getattr(user, "role", "user") or "user",
        "is_active": user.is_active,
        "kyc_status": "verified" if getattr(user, "is_kyc_verified", False) else "pending",
        "wallet_balance": None,
    }


class AuthLoginView(APIView):
    """POST /api/auth/login — JSON { email, password }; returns { access_token, user }."""

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            if not data and getattr(request, "body", None):
                try:
                    data = json.loads(request.body.decode("utf-8"))
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
            identifier = (data.get("email") or data.get("username") or "").strip()
            password = data.get("password") or ""
        except Exception:
            identifier, password = "", ""

        if not identifier or not password:
            return Response(
                {"detail": "Email and password required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # DEBUG: ensure default admin exists so login works out of the box
        if getattr(settings, "DEBUG", False):
            admin_user = User.objects.filter(username="admin").first()
            if admin_user is None:
                referral_code = uuid.uuid4().hex[:8].upper()
                while User.objects.filter(referral_code=referral_code).exists():
                    referral_code = uuid.uuid4().hex[:8].upper()
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    is_superuser=True,
                    is_staff=True,
                    role=User.Role.SUPER_ADMIN,
                    referral_code=referral_code,
                )
                admin_user.set_password("admin123")
                admin_user.save()

        user = User.objects.filter(email__iexact=identifier).first()
        if user is None:
            user = User.objects.filter(username__iexact=identifier).first()
        if not user or not user.check_password(password):
            # DEBUG: ensure admin/admin123 always works (reset password if they're trying that)
            if getattr(settings, "DEBUG", False) and password == "admin123":
                admin_user = User.objects.filter(username="admin").first()
                if admin_user and (identifier.lower() in ("admin", "admin@example.com")):
                    admin_user.set_password("admin123")
                    admin_user.save()
                    user = admin_user
            if not user or not user.check_password(password):
                return Response(
                    {"detail": "Invalid email or password."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        if not user.is_active:
            return Response(
                {"detail": "Account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "access_token": token.key,
            "user": _user_payload(user),
        })


class AuthLogoutView(APIView):
    """POST /api/auth/logout — optional; frontend clears token."""

    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."})


class AuthMeView(APIView):
    """GET /api/auth/me — current user (requires Authorization: Bearer <token>)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))


class CategoryListView(APIView):
    """GET /api/games/categories/ — active categories ordered by sort_order, name."""

    def get(self, request):
        qs = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        serializer = CategorySerializer(qs, many=True)
        return Response(serializer.data)


class CategoryAdminView(APIView):
    """
    Admin CRUD for Categories.
    GET /api/games/admin/categories/ — list all categories (admin only)
    POST /api/games/admin/categories/ — create category
    PATCH /api/games/admin/categories/<id>/ — update category
    DELETE /api/games/admin/categories/<id>/ — delete category
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        if pk:
            try:
                category = Category.objects.get(pk=pk)
                serializer = CategorySerializer(category)
                return Response(serializer.data)
            except Category.DoesNotExist:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        
        qs = Category.objects.all().order_by('sort_order', 'name')
        serializer = CategorySerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        name = data.get('name', '').strip()
        
        if not name:
            return Response({"detail": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate slug from name
        from django.utils.text import slugify
        slug = slugify(name)
        
        # Check if slug exists
        if Category.objects.filter(slug=slug).exists():
            slug = f"{slug}-{Category.objects.count() + 1}"
        
        category = Category.objects.create(
            name=name,
            slug=slug,
            icon=data.get('icon', ''),
            color=data.get('color', ''),
            is_active=data.get('is_active', True),
            sort_order=data.get('sort_order', 0),
        )
        
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        if 'name' in data:
            category.name = data['name']
        if 'icon' in data:
            category.icon = data['icon']
        if 'color' in data:
            category.color = data['color']
        if 'is_active' in data:
            category.is_active = data['is_active']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        
        category.save()
        
        serializer = CategorySerializer(category)
        return Response(serializer.data)

    def delete(self, request, pk):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        
        category.delete()
        return Response({"detail": "Category deleted."}, status=status.HTTP_204_NO_CONTENT)


class ProviderListView(APIView):
    """GET /api/games/providers/ — active providers."""

    def get(self, request):
        qs = Provider.objects.filter(is_active=True).order_by('sort_order', 'name')
        serializer = ProviderSerializer(qs, many=True)
        return Response(serializer.data)


class ProviderAdminView(APIView):
    """
    Admin CRUD for Providers.
    GET /api/games/admin/providers/ — list all providers (admin only)
    POST /api/games/admin/providers/ — create provider
    PATCH /api/games/admin/providers/<id>/ — update provider
    DELETE /api/games/admin/providers/<id>/ — delete provider
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        if pk:
            try:
                provider = Provider.objects.get(pk=pk)
                serializer = ProviderSerializer(provider)
                return Response(serializer.data)
            except Provider.DoesNotExist:
                return Response({"detail": "Provider not found."}, status=status.HTTP_404_NOT_FOUND)
        
        qs = Provider.objects.all().order_by('sort_order', 'name')
        serializer = ProviderSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        name = data.get('name', '').strip()
        
        if not name:
            return Response({"detail": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        provider = Provider.objects.create(
            name=name,
            logo=data.get('logo', ''),
            color=data.get('color', ''),
            is_active=data.get('is_active', True),
            sort_order=data.get('sort_order', 0),
        )
        
        serializer = ProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            provider = Provider.objects.get(pk=pk)
        except Provider.DoesNotExist:
            return Response({"detail": "Provider not found."}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        if 'name' in data:
            provider.name = data['name']
        if 'logo' in data:
            provider.logo = data['logo']
        if 'color' in data:
            provider.color = data['color']
        if 'is_active' in data:
            provider.is_active = data['is_active']
        if 'sort_order' in data:
            provider.sort_order = data['sort_order']
        
        provider.save()
        
        serializer = ProviderSerializer(provider)
        return Response(serializer.data)

    def delete(self, request, pk):
        if not _is_admin_role(request.user):
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            provider = Provider.objects.get(pk=pk)
        except Provider.DoesNotExist:
            return Response({"detail": "Provider not found."}, status=status.HTTP_404_NOT_FOUND)
        
        provider.delete()
        return Response({"detail": "Provider deleted."}, status=status.HTTP_204_NO_CONTENT)


class GameListView(APIView):
    """
    GET /api/games/ — list games.
    Query params: category (slug or id), provider (id), featured (bool), search.
    """

    def get(self, request):
        qs = Game.objects.filter(is_active=True).select_related('category', 'provider')

        category = request.query_params.get('category')
        if category:
            if category.isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(category__slug=category)

        provider = request.query_params.get('provider')
        if provider and provider.isdigit():
            qs = qs.filter(provider_id=int(provider))

        featured = request.query_params.get('featured', '').lower()
        if featured in ('true', '1', 'yes'):
            from django.db.models import Q
            qs = qs.filter(Q(is_hot=True) | Q(is_new=True))

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(name__icontains=search)

        qs = qs.order_by('sort_order', 'name')
        serializer = GameSerializer(qs, many=True)
        return Response(serializer.data)


class GameDetailView(APIView):
    """GET /api/games/<slug>/ or /api/games/<pk>/ — single game by slug or ID."""

    def get(self, request, slug=None, pk=None):
        try:
            if pk is not None:
                game = Game.objects.select_related('category', 'provider').get(
                    pk=pk, is_active=True
                )
            elif slug is not None:
                game = Game.objects.select_related('category', 'provider').get(
                    slug=slug, is_active=True
                )
            else:
                return Response(
                    {'detail': 'Game identifier required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Game.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GameSerializer(game)
        return Response(serializer.data)


class PromoBannerListView(APIView):
    """
    GET /api/config/banners/ — active promo banners within start_at/end_at.
    POST /api/config/banners/ — create promo banner (admin only).
    Optional query: position (no DB field; can be used later).
    """

    def get(self, request):
        now = timezone.now()
        qs = PromoBanner.objects.filter(is_active=True)
        # Within date range: no start_at or start_at <= now; no end_at or end_at >= now
        from django.db.models import Q
        qs = qs.filter(
            Q(start_at__isnull=True) | Q(start_at__lte=now),
            Q(end_at__isnull=True) | Q(end_at__gte=now),
        ).order_by('sort_order', '-created_at')

        # Optional position filter (e.g. if we add a position field later)
        position = request.query_params.get('position', '').strip()
        if position:
            # PromoBanner has no position field; ignore for now or add to model later
            pass

        serializer = PromoBannerSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        from rest_framework.permissions import IsAuthenticated
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        if not _is_admin_role(request.user):
            return Response({"detail": "Only admins can create banners."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({"detail": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)

        banner = PromoBanner.objects.create(
            title=title,
            description=data.get('description', ''),
            image_url=data.get('image_url', ''),
            link_url=data.get('link_url', ''),
            sort_order=data.get('sort_order', 0),
            is_active=data.get('is_active', True),
            start_at=data.get('start_at'),
            end_at=data.get('end_at'),
        )
        serializer = PromoBannerSerializer(banner)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _is_admin_role(user):
    """Allow staff/superuser or role in powerhouse, super_admin, master (admin hierarchy)."""
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    # Role hierarchy: powerhouse > super_admin > master > user
    return role in (User.Role.POWERHOUSE, User.Role.SUPER_ADMIN, User.Role.MASTER)


class UserListCreateView(APIView):
    """
    GET /api/users/ — list users (admin only).
    POST /api/users/ or POST /api/users — create user (admin only). Body: email, username, password, full_name, role.
    """

    permission_classes = [IsAuthenticated]

    def _check_admin(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def get(self, request):
        err = self._check_admin(request)
        if err is not None:
            return err
        qs = User.objects.all().order_by("-date_joined")
        role_filter = request.query_params.get("role", "").strip()
        if role_filter:
            qs = qs.filter(role=role_filter)
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(name__icontains=search)
            )
        return Response([_user_payload(u) for u in qs])

    def post(self, request):
        err = self._check_admin(request)
        if err is not None:
            return err
        try:
            data = request.data
            if not data and getattr(request, "body", None):
                try:
                    data = json.loads(request.body.decode("utf-8"))
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        email = (data.get("email") or "").strip()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        full_name = (data.get("full_name") or "").strip()
        role = (data.get("role") or "user").strip().lower()

        if not username:
            return Response(
                {"detail": "username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email:
            return Response(
                {"detail": "email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"detail": "password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_map = {
            "user": User.Role.USER,
            "master": User.Role.MASTER,
            "super_admin": User.Role.SUPER_ADMIN,
            "powerhouse": User.Role.POWERHOUSE,
            "admin": User.Role.SUPER_ADMIN,
        }
        role_value = role_map.get(role, User.Role.USER)

        # Generate a unique referral code
        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        # Build user object with referral_code before saving
        user = User(
            username=username,
            email=email,
            name=full_name or username,
            role=role_value,
            referral_code=referral_code,
        )
        user.set_password(password)
        user.save()

        Wallet.objects.get_or_create(user=user, defaults={"balance": 0, "currency": "INR"})
        UserSettings.objects.get_or_create(user=user)

        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


# =============================================================================
# DEPOSIT VIEWS
# =============================================================================

class DepositListCreateView(APIView):
    """
    GET /api/transactions/deposits — list deposits (user sees own, admin sees all).
    POST /api/transactions/deposits — create deposit request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin_role(request.user):
            qs = DepositRequest.objects.all()
        else:
            qs = DepositRequest.objects.filter(user=request.user)
        
        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        qs = qs.select_related('user', 'payment_method', 'approved_by').order_by('-created_at')
        serializer = DepositRequestSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        payment_method_id = data.get('payment_method')
        amount = data.get('amount')
        transaction_code = data.get('transaction_code', '')
        receipt_file_url = data.get('receipt_file_url', '')

        if not payment_method_id or not amount:
            return Response(
                {"detail": "payment_method and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_method = PaymentMethod.objects.get(pk=payment_method_id, is_active=True)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"detail": "Invalid payment method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deposit = DepositRequest.objects.create(
            user=request.user,
            payment_method=payment_method,
            amount=Decimal(str(amount)),
            transaction_code=transaction_code,
            receipt_file_url=receipt_file_url,
            status=DepositRequest.DepositStatus.PENDING,
        )
        serializer = DepositRequestSerializer(deposit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DepositApproveView(APIView):
    """PATCH /api/transactions/deposits/<id>/approve — approve deposit (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can approve deposits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deposit = DepositRequest.objects.select_related('user').get(pk=pk)
        except DepositRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if deposit.status != DepositRequest.DepositStatus.PENDING:
            return Response(
                {"detail": "Deposit already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            deposit.status = DepositRequest.DepositStatus.APPROVED
            deposit.approved_by = request.user
            deposit.approved_at = timezone.now()
            deposit.save()

            # Credit user wallet
            wallet, _ = Wallet.objects.get_or_create(
                user=deposit.user, defaults={"balance": 0, "currency": "INR"}
            )
            wallet.balance += deposit.amount
            wallet.save()

            # Create transaction record
            Transaction.objects.create(
                user=deposit.user,
                type=Transaction.TransactionType.DEPOSIT,
                amount=deposit.amount,
                method=deposit.payment_method.name,
                reference=deposit.transaction_code,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        serializer = DepositRequestSerializer(deposit)
        return Response(serializer.data)


class DepositRejectView(APIView):
    """PATCH /api/transactions/deposits/<id>/reject — reject deposit (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can reject deposits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deposit = DepositRequest.objects.get(pk=pk)
        except DepositRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if deposit.status != DepositRequest.DepositStatus.PENDING:
            return Response(
                {"detail": "Deposit already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deposit.status = DepositRequest.DepositStatus.REJECTED
        deposit.approved_by = request.user
        deposit.approved_at = timezone.now()
        deposit.save()

        serializer = DepositRequestSerializer(deposit)
        return Response(serializer.data)


# =============================================================================
# WITHDRAWAL VIEWS
# =============================================================================

class WithdrawalListCreateView(APIView):
    """
    GET /api/transactions/withdrawals — list withdrawals.
    POST /api/transactions/withdrawals — create withdrawal request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin_role(request.user):
            qs = WithdrawalRequest.objects.all()
        else:
            qs = WithdrawalRequest.objects.filter(user=request.user)

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.select_related('user', 'payment_method', 'approved_by').order_by('-created_at')
        serializer = WithdrawalRequestSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        payment_method_id = data.get('payment_method')
        amount = data.get('amount')
        account_number = data.get('account_number', '')
        account_name = data.get('account_name', '')

        if not payment_method_id or not amount:
            return Response(
                {"detail": "payment_method and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_method = PaymentMethod.objects.get(pk=payment_method_id, is_active=True)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"detail": "Invalid payment method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check user has enough balance
        wallet, _ = Wallet.objects.get_or_create(
            user=request.user, defaults={"balance": 0, "currency": "INR"}
        )
        amount_decimal = Decimal(str(amount))
        if wallet.balance < amount_decimal:
            return Response(
                {"detail": "Insufficient balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        withdrawal = WithdrawalRequest.objects.create(
            user=request.user,
            payment_method=payment_method,
            amount=amount_decimal,
            account_number=account_number,
            account_name=account_name,
            status=WithdrawalRequest.WithdrawalStatus.PENDING,
        )
        serializer = WithdrawalRequestSerializer(withdrawal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WithdrawalApproveView(APIView):
    """PATCH /api/transactions/withdrawals/<id>/approve — approve withdrawal (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can approve withdrawals."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            withdrawal = WithdrawalRequest.objects.select_related('user').get(pk=pk)
        except WithdrawalRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if withdrawal.status != WithdrawalRequest.WithdrawalStatus.PENDING:
            return Response(
                {"detail": "Withdrawal already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            # Deduct from wallet
            wallet, _ = Wallet.objects.get_or_create(
                user=withdrawal.user, defaults={"balance": 0, "currency": "INR"}
            )
            if wallet.balance < withdrawal.amount:
                return Response(
                    {"detail": "User has insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet.balance -= withdrawal.amount
            wallet.save()

            withdrawal.status = WithdrawalRequest.WithdrawalStatus.APPROVED
            withdrawal.approved_by = request.user
            withdrawal.approved_at = timezone.now()
            withdrawal.reference = f"WD-{uuid.uuid4().hex[:8].upper()}"
            withdrawal.save()

            # Create transaction record
            Transaction.objects.create(
                user=withdrawal.user,
                type=Transaction.TransactionType.WITHDRAWAL,
                amount=withdrawal.amount,
                method=withdrawal.payment_method.name,
                reference=withdrawal.reference,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        serializer = WithdrawalRequestSerializer(withdrawal)
        return Response(serializer.data)


class WithdrawalRejectView(APIView):
    """PATCH /api/transactions/withdrawals/<id>/reject — reject withdrawal (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can reject withdrawals."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            withdrawal = WithdrawalRequest.objects.get(pk=pk)
        except WithdrawalRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if withdrawal.status != WithdrawalRequest.WithdrawalStatus.PENDING:
            return Response(
                {"detail": "Withdrawal already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        withdrawal.status = WithdrawalRequest.WithdrawalStatus.REJECTED
        withdrawal.approved_by = request.user
        withdrawal.approved_at = timezone.now()
        withdrawal.save()

        serializer = WithdrawalRequestSerializer(withdrawal)
        return Response(serializer.data)


# =============================================================================
# COINS/WALLET VIEWS
# =============================================================================

class CoinMintView(APIView):
    """POST /api/coins/mint — mint coins to user (admin only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can mint coins."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        to_user_id = data.get('to_user_id')
        amount = data.get('amount')
        description = data.get('description', 'Admin mint')

        if not to_user_id or not amount:
            return Response(
                {"detail": "to_user_id and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            to_user = User.objects.get(pk=to_user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        amount_decimal = Decimal(str(amount))
        with db_transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(
                user=to_user, defaults={"balance": 0, "currency": "INR"}
            )
            wallet.balance += amount_decimal
            wallet.save()

            Transaction.objects.create(
                user=to_user,
                type=Transaction.TransactionType.BONUS,
                amount=amount_decimal,
                method='admin_mint',
                reference=description,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        return Response({
            "detail": f"Minted {amount} coins to {to_user.username}.",
            "new_balance": str(wallet.balance),
        })


class CoinTransferView(APIView):
    """POST /api/coins/transfer — transfer coins between users."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        to_user_id = data.get('to_user_id')
        amount = data.get('amount')
        description = data.get('description', 'Transfer')

        if not to_user_id or not amount:
            return Response(
                {"detail": "to_user_id and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            to_user = User.objects.get(pk=to_user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if to_user.pk == request.user.pk:
            return Response(
                {"detail": "Cannot transfer to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_decimal = Decimal(str(amount))
        with db_transaction.atomic():
            from_wallet, _ = Wallet.objects.get_or_create(
                user=request.user, defaults={"balance": 0, "currency": "INR"}
            )
            if from_wallet.balance < amount_decimal:
                return Response(
                    {"detail": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            to_wallet, _ = Wallet.objects.get_or_create(
                user=to_user, defaults={"balance": 0, "currency": "INR"}
            )

            from_wallet.balance -= amount_decimal
            from_wallet.save()

            to_wallet.balance += amount_decimal
            to_wallet.save()

            # Record both sides of transfer
            ref = f"TRF-{uuid.uuid4().hex[:8].upper()}"
            Transaction.objects.create(
                user=request.user,
                type=Transaction.TransactionType.TRANSFER,
                amount=-amount_decimal,
                method='transfer_out',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )
            Transaction.objects.create(
                user=to_user,
                type=Transaction.TransactionType.TRANSFER,
                amount=amount_decimal,
                method='transfer_in',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        return Response({
            "detail": f"Transferred {amount} coins to {to_user.username}.",
            "new_balance": str(from_wallet.balance),
        })


class CoinTransactionListView(APIView):
    """GET /api/coins/transactions — list transactions for user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin_role(request.user):
            qs = Transaction.objects.all()
        else:
            qs = Transaction.objects.filter(user=request.user)

        type_filter = request.query_params.get('type', '').strip()
        if type_filter:
            qs = qs.filter(type=type_filter)

        qs = qs.select_related('user').order_by('-created_at')
        serializer = TransactionSerializer(qs, many=True)
        return Response(serializer.data)


class ExportTransactionsView(APIView):
    """GET /api/coins/transactions/export — export user's transactions as CSV."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        user = request.user
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Type', 'Amount', 'Method', 'Reference', 'Status', 'Date'])

        for txn in transactions:
            writer.writerow([
                txn.id,
                txn.type,
                str(txn.amount),
                txn.method or '',
                txn.reference or '',
                txn.status,
                txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return response


class WalletBalanceView(APIView):
    """GET /api/wallets/my-balance — get current user's wallet balance."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(
            user=request.user, defaults={"balance": 0, "currency": "INR"}
        )
        return Response({
            "balance": str(wallet.balance),
            "currency": wallet.currency,
        })


class WalletUserBalanceView(APIView):
    """GET /api/wallets/<userId> — get specific user's balance (admin only)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view other users' wallets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        wallet, _ = Wallet.objects.get_or_create(
            user=user, defaults={"balance": 0, "currency": "INR"}
        )
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


# =============================================================================
# BET VIEWS
# =============================================================================

class BetListCreateView(APIView):
    """
    GET /api/bets — list bets.
    POST /api/bets — place a bet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin_role(request.user):
            qs = Bet.objects.all()
        else:
            qs = Bet.objects.filter(user=request.user)

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.select_related('user', 'game', 'settled_by').order_by('-bet_at')
        serializer = BetSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        game_id = data.get('game')
        game_name = data.get('game_name', '')
        game_type = data.get('game_type', '')
        category = data.get('category', '')
        bet_amount = data.get('bet_amount')
        odds = data.get('odds')

        if not bet_amount:
            return Response(
                {"detail": "bet_amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_decimal = Decimal(str(bet_amount))

        # Check balance
        wallet, _ = Wallet.objects.get_or_create(
            user=request.user, defaults={"balance": 0, "currency": "INR"}
        )
        if wallet.balance < amount_decimal:
            return Response(
                {"detail": "Insufficient balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        game = None
        if game_id:
            try:
                game = Game.objects.get(pk=game_id)
                game_name = game_name or game.name
            except Game.DoesNotExist:
                return Response(
                    {"detail": f"Game with id {game_id} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with db_transaction.atomic():
            # Deduct bet amount
            wallet.balance -= amount_decimal
            wallet.save()

            bet = Bet.objects.create(
                user=request.user,
                game=game,
                game_name=game_name,
                game_type=game_type,
                category=category,
                bet_amount=amount_decimal,
                odds=Decimal(str(odds)) if odds else None,
                status=Bet.BetStatus.PENDING,
            )

            Transaction.objects.create(
                user=request.user,
                type=Transaction.TransactionType.BET,
                amount=-amount_decimal,
                method='bet',
                reference=f"BET-{bet.pk}",
                status=Transaction.TransactionStatus.COMPLETED,
            )

        serializer = BetSerializer(bet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExportBetsView(APIView):
    """GET /api/bets/export — export user's bet history as CSV."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        user = request.user
        bets = Bet.objects.filter(user=user).select_related('game').order_by('-bet_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bet_history.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Game', 'Category', 'Bet Amount', 'Odds', 'Win Amount', 'Status', 'Date'])

        for bet in bets:
            writer.writerow([
                bet.id,
                bet.game_name or (bet.game.name if bet.game else 'N/A'),
                bet.category or '',
                str(bet.bet_amount),
                str(bet.odds) if bet.odds else '',
                str(bet.win_amount) if bet.win_amount else '0',
                bet.status,
                bet.bet_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        return response


class BetSettleView(APIView):
    """POST /api/bets/<id>/settle — settle a bet (admin only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can settle bets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            bet = Bet.objects.select_related('user').get(pk=pk)
        except Bet.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if bet.status != Bet.BetStatus.PENDING:
            return Response(
                {"detail": "Bet already settled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data
        result = data.get('result')  # 'won' or 'lost'
        actual_win = Decimal(str(data.get('actual_win', 0)))

        if result not in ('won', 'lost'):
            return Response(
                {"detail": "result must be 'won' or 'lost'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            bet.status = Bet.BetStatus.WON if result == 'won' else Bet.BetStatus.LOST
            bet.win_amount = actual_win
            bet.settled_by = request.user
            bet.settled_at = timezone.now()
            bet.save()

            if result == 'won' and actual_win > 0:
                wallet, _ = Wallet.objects.get_or_create(
                    user=bet.user, defaults={"balance": 0, "currency": "INR"}
                )
                wallet.balance += actual_win
                wallet.save()

                Transaction.objects.create(
                    user=bet.user,
                    type=Transaction.TransactionType.WIN,
                    amount=actual_win,
                    method='bet_win',
                    reference=f"WIN-BET-{bet.pk}",
                    status=Transaction.TransactionStatus.COMPLETED,
                )

        serializer = BetSerializer(bet)
        return Response(serializer.data)


class BetCancelView(APIView):
    """POST /api/bets/<id>/cancel — cancel a bet and refund (admin only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can cancel bets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            bet = Bet.objects.select_related('user').get(pk=pk)
        except Bet.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if bet.status != Bet.BetStatus.PENDING:
            return Response(
                {"detail": "Bet already settled or cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            bet.status = Bet.BetStatus.CANCELLED
            bet.settled_by = request.user
            bet.settled_at = timezone.now()
            bet.save()

            # Refund bet amount
            wallet, _ = Wallet.objects.get_or_create(
                user=bet.user, defaults={"balance": 0, "currency": "INR"}
            )
            wallet.balance += bet.bet_amount
            wallet.save()

            Transaction.objects.create(
                user=bet.user,
                type=Transaction.TransactionType.REFUND,
                amount=bet.bet_amount,
                method='bet_cancel_refund',
                reference=f"REFUND-BET-{bet.pk}",
                status=Transaction.TransactionStatus.COMPLETED,
            )

        serializer = BetSerializer(bet)
        return Response(serializer.data)


# =============================================================================
# GAME VIEWS (ADDITIONAL)
# =============================================================================

class GameLaunchView(APIView):
    """POST /api/games/<slug>/launch or /api/games/<pk>/launch — launch a game (returns game URL/info)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None, pk=None):
        try:
            if pk is not None:
                game = Game.objects.select_related('category', 'provider').get(
                    pk=pk, is_active=True
                )
            elif slug is not None:
                game = Game.objects.select_related('category', 'provider').get(
                    slug=slug, is_active=True
                )
            else:
                return Response({"detail": "Game identifier required."}, status=status.HTTP_400_BAD_REQUEST)
        except Game.DoesNotExist:
            return Response({"detail": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

        # Increment player count (simplified)
        game.players = (game.players or 0) + 1
        game.save(update_fields=['players'])

        return Response({
            "game_id": game.pk,
            "game_slug": game.slug,
            "game_name": game.name,
            "provider": game.provider.name if game.provider else None,
            "launch_url": f"/play/{game.slug}",  # Placeholder URL
            "session_id": uuid.uuid4().hex,
        })


class AdminGameListView(APIView):
    """GET /api/games/admin/all — list all games for admin."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view all games."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = Game.objects.select_related('category', 'provider').order_by('sort_order', 'name')
        serializer = GameSerializer(qs, many=True)
        return Response(serializer.data)


class AdminGameCreateUpdateView(APIView):
    """
    POST /api/games/admin/games — create game.
    PATCH /api/games/admin/games/<id> — update game.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can create games."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        required = ['name', 'slug', 'category', 'provider']
        for field in required:
            if not data.get(field):
                return Response(
                    {"detail": f"{field} is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if Game.objects.filter(slug=data['slug']).exists():
            return Response(
                {"detail": "A game with this slug already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            category = Category.objects.get(pk=data['category'])
            provider = Provider.objects.get(pk=data['provider'])
        except (Category.DoesNotExist, Provider.DoesNotExist):
            return Response(
                {"detail": "Invalid category or provider."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        game = Game.objects.create(
            name=data['name'],
            slug=data['slug'],
            category=category,
            provider=provider,
            image=data.get('image', ''),
            min_bet=Decimal(str(data.get('min_bet', 0))),
            max_bet=Decimal(str(data.get('max_bet', 0))),
            rating=Decimal(str(data.get('rating', 0))) if data.get('rating') else None,
            rtp=Decimal(str(data.get('rtp', 0))) if data.get('rtp') else None,
            is_hot=data.get('is_hot', False),
            is_new=data.get('is_new', False),
            description=data.get('description', ''),
            how_to_play=data.get('how_to_play', []),
            features=data.get('features', []),
            is_active=data.get('is_active', True),
        )

        serializer = GameSerializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can update games."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if pk is None:
            return Response(
                {"detail": "Game ID required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            game = Game.objects.get(pk=pk)
        except Game.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        update_fields = []

        for field in ['name', 'image', 'description', 'is_hot', 'is_new', 'is_active', 'sort_order']:
            if field in data:
                setattr(game, field, data[field])
                update_fields.append(field)

        for field in ['min_bet', 'max_bet', 'rating', 'rtp']:
            if field in data:
                setattr(game, field, Decimal(str(data[field])) if data[field] else None)
                update_fields.append(field)

        if 'how_to_play' in data:
            game.how_to_play = data['how_to_play']
            update_fields.append('how_to_play')

        if 'features' in data:
            game.features = data['features']
            update_fields.append('features')

        if update_fields:
            game.save(update_fields=update_fields)

        serializer = GameSerializer(game)
        return Response(serializer.data)

    def delete(self, request, pk=None):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can delete games."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if pk is None:
            return Response(
                {"detail": "Game ID required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            game = Game.objects.get(pk=pk)
        except Game.DoesNotExist:
            return Response({"detail": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

        game_name = game.name
        game.delete()
        return Response({"detail": f"Game '{game_name}' deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# KYC VIEWS
# =============================================================================

class KYCUploadView(APIView):
    """POST /api/kyc/upload — upload KYC documents."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        document_type = data.get('document_type', 'id_card')
        document_url = data.get('document_url', '')
        document_number = data.get('document_number', '')

        user = request.user
        user.kyc_document = {
            'type': document_type,
            'url': document_url,
            'number': document_number,
            'submitted_at': timezone.now().isoformat(),
        }
        user.is_kyc_verified = False  # Reset to pending
        user.kyc_reject_reason = ''
        user.save()

        return Response({
            "detail": "KYC documents uploaded successfully.",
            "kyc_status": "pending",
        })


class KYCStatusView(APIView):
    """GET /api/kyc/status — get current user's KYC status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "is_verified": user.is_kyc_verified,
            "kyc_document": user.kyc_document,
            "reject_reason": user.kyc_reject_reason,
            "status": "verified" if user.is_kyc_verified else ("rejected" if user.kyc_reject_reason else "pending"),
        })


class KYCPendingView(APIView):
    """GET /api/kyc/pending — list pending KYC submissions (admin only)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view pending KYC."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Users with KYC documents but not verified and no rejection
        users = User.objects.filter(
            is_kyc_verified=False,
            kyc_reject_reason='',
        ).exclude(kyc_document={}).order_by('-updated_at')

        data = []
        for u in users:
            data.append({
                "id": str(u.pk),
                "username": u.username,
                "email": u.email,
                "kyc_document": u.kyc_document,
                "submitted_at": u.kyc_document.get('submitted_at') if u.kyc_document else None,
            })

        return Response(data)


class KYCApproveRejectView(APIView):
    """
    PATCH /api/kyc/<id>/approve — approve KYC.
    PATCH /api/kyc/<id>/reject — reject KYC.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, action=None):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can approve/reject KYC."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            user.is_kyc_verified = True
            user.kyc_reject_reason = ''
            user.save()
            return Response({"detail": "KYC approved.", "is_verified": True})
        elif action == 'reject':
            reason = request.data.get('review_notes', 'Rejected by admin')
            user.is_kyc_verified = False
            user.kyc_reject_reason = reason
            user.save()
            return Response({"detail": "KYC rejected.", "is_verified": False, "reason": reason})
        else:
            return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# SUPPORT/TICKET VIEWS
# =============================================================================

class TicketListCreateView(APIView):
    """
    GET /api/support/tickets — list tickets.
    POST /api/support/tickets — create ticket.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _is_admin_role(request.user):
            qs = Ticket.objects.all()
        else:
            qs = Ticket.objects.filter(user=request.user)

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.select_related('user').prefetch_related('messages__user').order_by('-last_update_at')
        serializer = TicketSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        subject = data.get('subject', '').strip()
        category = data.get('category', '')
        message = data.get('message', '').strip()

        if not subject:
            return Response(
                {"detail": "subject is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket = Ticket.objects.create(
            user=request.user,
            subject=subject,
            category=category,
            status=Ticket.TicketStatus.OPEN,
        )

        if message:
            TicketMessage.objects.create(
                ticket=ticket,
                user=request.user,
                message=message,
                is_staff=False,
            )

        serializer = TicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TicketReplyView(APIView):
    """POST /api/support/tickets/<id>/reply — reply to ticket."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Users can only reply to their own tickets, admins can reply to any
        if not _is_admin_role(request.user) and ticket.user != request.user:
            return Response(
                {"detail": "You can only reply to your own tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {"detail": "message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_staff = _is_admin_role(request.user)

        TicketMessage.objects.create(
            ticket=ticket,
            user=request.user,
            message=message,
            is_staff=is_staff,
        )

        # Update ticket status if admin replies
        if is_staff and ticket.status == Ticket.TicketStatus.OPEN:
            ticket.status = Ticket.TicketStatus.IN_PROGRESS
            ticket.save()

        ticket.refresh_from_db()
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)


class TicketCloseView(APIView):
    """PATCH /api/support/tickets/<id>/close — close ticket."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Users can close their own tickets, admins can close any
        if not _is_admin_role(request.user) and ticket.user != request.user:
            return Response(
                {"detail": "You can only close your own tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ticket.status = Ticket.TicketStatus.CLOSED
        ticket.save()

        serializer = TicketSerializer(ticket)
        return Response(serializer.data)


# =============================================================================
# ADMIN DASHBOARD VIEWS
# =============================================================================

class AdminDashboardStatsView(APIView):
    """GET /api/dashboard/admin-stats — dashboard statistics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view dashboard stats."},
                status=status.HTTP_403_FORBIDDEN,
            )

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_deposits = DepositRequest.objects.filter(
            status=DepositRequest.DepositStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0
        total_withdrawals = WithdrawalRequest.objects.filter(
            status=WithdrawalRequest.WithdrawalStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0
        pending_deposits = DepositRequest.objects.filter(
            status=DepositRequest.DepositStatus.PENDING
        ).count()
        pending_withdrawals = WithdrawalRequest.objects.filter(
            status=WithdrawalRequest.WithdrawalStatus.PENDING
        ).count()
        total_bets = Bet.objects.count()
        pending_kyc = User.objects.filter(
            is_kyc_verified=False, kyc_reject_reason=''
        ).exclude(kyc_document={}).count()
        open_tickets = Ticket.objects.filter(
            status__in=[Ticket.TicketStatus.OPEN, Ticket.TicketStatus.IN_PROGRESS]
        ).count()

        return Response({
            "total_users": total_users,
            "active_users": active_users,
            "total_deposits": str(total_deposits),
            "total_withdrawals": str(total_withdrawals),
            "pending_deposits": pending_deposits,
            "pending_withdrawals": pending_withdrawals,
            "total_bets": total_bets,
            "pending_kyc": pending_kyc,
            "open_tickets": open_tickets,
        })


# =============================================================================
# SYSTEM CONFIG VIEWS
# =============================================================================

class SystemConfigView(APIView):
    """
    GET /api/config/system — get system configs.
    POST /api/config/system — create/update config (admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view system config."},
                status=status.HTTP_403_FORBIDDEN,
            )

        configs = SystemConfig.objects.all()
        serializer = SystemConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can update system config."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config_key = request.query_params.get('config_key') or request.data.get('config_key')
        config_value = request.query_params.get('config_value') or request.data.get('config_value')

        if not config_key:
            return Response(
                {"detail": "config_key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config, created = SystemConfig.objects.update_or_create(
            key=config_key,
            defaults={
                'value': config_value or '',
                'updated_by': request.user,
            }
        )

        serializer = SystemConfigSerializer(config)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# =============================================================================
# PAYMENT METHOD VIEWS
# =============================================================================

class PaymentMethodListCreateView(APIView):
    """
    GET /api/config/payment-methods — list payment methods.
    POST /api/config/payment-methods — create payment method (admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
        serializer = PaymentMethodSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can create payment methods."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        if not data.get('name'):
            return Response(
                {"detail": "name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pm = PaymentMethod.objects.create(
            name=data['name'],
            icon=data.get('icon', ''),
            min_limit=Decimal(str(data.get('min_limit', 0))),
            max_limit=Decimal(str(data.get('max_limit', 0))),
            has_qr=data.get('has_qr', False),
            is_active=data.get('is_active', True),
            sort_order=data.get('sort_order', 0),
        )

        serializer = PaymentMethodSerializer(pm)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentMethodUpdateView(APIView):
    """PATCH /api/config/payment-methods/<id> — update payment method (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can update payment methods."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            pm = PaymentMethod.objects.get(pk=pk)
        except PaymentMethod.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        for field in ['name', 'icon', 'has_qr', 'is_active', 'sort_order']:
            if field in data:
                setattr(pm, field, data[field])

        for field in ['min_limit', 'max_limit']:
            if field in data:
                setattr(pm, field, Decimal(str(data[field])))

        pm.save()
        serializer = PaymentMethodSerializer(pm)
        return Response(serializer.data)


# =============================================================================
# BONUS RULES VIEWS
# =============================================================================

class BonusRuleListCreateView(APIView):
    """
    GET /api/config/bonus-rules — list bonus rules.
    POST /api/config/bonus-rules — create bonus rule (admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view bonus rules."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # For now, return system config entries related to bonuses
        configs = SystemConfig.objects.filter(key__startswith='bonus_')
        data = [{"key": c.key, "value": c.value} for c in configs]
        return Response(data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can create bonus rules."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        rule_key = data.get('rule_key', '')
        rule_value = data.get('rule_value', '')

        if not rule_key:
            return Response(
                {"detail": "rule_key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config, created = SystemConfig.objects.update_or_create(
            key=f"bonus_{rule_key}",
            defaults={'value': rule_value, 'updated_by': request.user}
        )

        return Response({
            "key": config.key,
            "value": config.value,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# =============================================================================
# LIMITS VIEWS
# =============================================================================

class LimitListCreateView(APIView):
    """
    GET /api/config/limits — list limits.
    POST /api/config/limits — create limit (admin only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can view limits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Return system config entries related to limits
        configs = SystemConfig.objects.filter(key__startswith='limit_')
        data = [{"key": c.key, "value": c.value} for c in configs]
        return Response(data)

    def post(self, request):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can create limits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        limit_key = data.get('limit_key', '')
        limit_value = data.get('limit_value', '')

        if not limit_key:
            return Response(
                {"detail": "limit_key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config, created = SystemConfig.objects.update_or_create(
            key=f"limit_{limit_key}",
            defaults={'value': limit_value, 'updated_by': request.user}
        )

        return Response({
            "key": config.key,
            "value": config.value,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# =============================================================================
# USER DETAIL VIEWS
# =============================================================================

class UserDetailView(APIView):
    """
    GET /api/users/<id> — get user details.
    PATCH /api/users/<id> — update user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Users can view their own profile, admins can view any
        if str(request.user.pk) != str(pk) and not _is_admin_role(request.user):
            return Response(
                {"detail": "You can only view your own profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.select_related('wallet').get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(_user_payload(user))

    def patch(self, request, pk):
        # Users can update their own profile, admins can update any
        if str(request.user.pk) != str(pk) and not _is_admin_role(request.user):
            return Response(
                {"detail": "You can only update your own profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        allowed_fields = ['name', 'phone', 'whatsapp', 'address', 'city', 'country']

        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        # Only admins can change these fields
        if _is_admin_role(request.user):
            if 'is_active' in data:
                user.is_active = data['is_active']
            if 'status' in data:
                user.status = data['status']

        user.save()
        return Response(_user_payload(user))


class UserSuspendView(APIView):
    """POST /api/users/<id>/suspend — suspend user (admin only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can suspend users."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        user.status = User.Status.SUSPENDED
        user.is_active = False
        user.save()

        return Response({"detail": f"User {user.username} has been suspended."})


class UserChangeRoleView(APIView):
    """PATCH /api/users/<id>/change-role — change user role (admin only)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _is_admin_role(request.user):
            return Response(
                {"detail": "Only admins can change user roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_role = request.query_params.get('new_role', '').strip().lower()
        if not new_role:
            return Response(
                {"detail": "new_role query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        role_map = {
            "user": User.Role.USER,
            "master": User.Role.MASTER,
            "super_admin": User.Role.SUPER_ADMIN,
            "powerhouse": User.Role.POWERHOUSE,
            "admin": User.Role.SUPER_ADMIN,
        }

        if new_role not in role_map:
            return Response(
                {"detail": f"Invalid role. Must be one of: {', '.join(role_map.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = role_map[new_role]
        user.save()

        return Response({
            "detail": f"User {user.username} role changed to {new_role}.",
            "user": _user_payload(user),
        })


# =============================================================================
# AUTH REGISTER VIEW
# =============================================================================

class AuthRegisterView(APIView):
    """POST /api/auth/register — register new user."""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        email = (data.get('email') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        full_name = (data.get('full_name') or data.get('name') or '').strip()
        referral_code_used = (data.get('referral_code') or '').strip()

        if not username:
            return Response(
                {"detail": "username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email:
            return Response(
                {"detail": "email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"detail": "password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate unique referral code
        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        user = User(
            username=username,
            email=email,
            name=full_name or username,
            role=User.Role.USER,
            referral_code=referral_code,
        )
        user.set_password(password)
        user.save()

        Wallet.objects.get_or_create(user=user, defaults={"balance": 0, "currency": "INR"})
        UserSettings.objects.get_or_create(user=user)

        # Create auth token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "access_token": token.key,
            "user": _user_payload(user),
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# USER STATS VIEW
# =============================================================================

class UserStatsView(APIView):
    """GET /api/users/me/stats — get current user's gaming statistics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get all user's bets
        bets = Bet.objects.filter(user=user)

        # Calculate statistics
        total_bets_count = bets.count()
        total_bet_amount = bets.aggregate(total=Sum('bet_amount'))['total'] or Decimal('0')
        
        won_bets = bets.filter(status=Bet.BetStatus.WON)
        won_count = won_bets.count()
        total_winnings = won_bets.aggregate(total=Sum('win_amount'))['total'] or Decimal('0')

        lost_bets = bets.filter(status=Bet.BetStatus.LOST)
        lost_count = lost_bets.count()

        # Win rate calculation
        settled_bets = won_count + lost_count
        win_rate = (won_count / settled_bets * 100) if settled_bets > 0 else 0

        # Get wallet balance
        wallet, _ = Wallet.objects.get_or_create(
            user=user, defaults={"balance": 0, "currency": "INR"}
        )

        # Get recent activity (last 5 bets)
        recent_bets = bets.select_related('game').order_by('-bet_at')[:5]
        recent_activity = []
        for bet in recent_bets:
            recent_activity.append({
                "id": bet.pk,
                "game_name": bet.game_name or (bet.game.name if bet.game else "Unknown"),
                "result": bet.status,
                "amount": str(bet.win_amount if bet.status == Bet.BetStatus.WON else -bet.bet_amount),
                "bet_at": bet.bet_at.isoformat() if bet.bet_at else None,
            })

        # Get active bets (pending)
        active_bets = bets.filter(status=Bet.BetStatus.PENDING).select_related('game')[:5]
        active_bets_data = []
        for bet in active_bets:
            active_bets_data.append({
                "id": bet.pk,
                "game_name": bet.game_name or (bet.game.name if bet.game else "Unknown"),
                "game_type": bet.game_type,
                "odds": str(bet.odds) if bet.odds else None,
                "stake": str(bet.bet_amount),
                "potential_win": str(bet.bet_amount * bet.odds) if bet.odds else str(bet.bet_amount),
                "status": "pending",
            })

        return Response({
            "balance": str(wallet.balance),
            "currency": wallet.currency,
            "total_winnings": str(total_winnings),
            "total_bet_amount": str(total_bet_amount),
            "total_bets_count": total_bets_count,
            "won_count": won_count,
            "lost_count": lost_count,
            "win_rate": round(win_rate, 1),
            "recent_activity": recent_activity,
            "active_bets": active_bets_data,
        })


# =============================================================================
# USER BONUSES VIEW
# =============================================================================

class UserBonusesView(APIView):
    """GET /api/bonuses/my — get current user's bonuses."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        bonuses = Bonus.objects.filter(user=user).order_by('-created_at')

        data = []
        for bonus in bonuses:
            data.append({
                "id": str(bonus.pk),
                "name": bonus.name,
                "type": bonus.type,
                "amount": str(bonus.amount),
                "wagering": str(bonus.wagering),
                "wagering_progress": str(bonus.wagering_progress),
                "expires_at": bonus.expires_at.isoformat() if bonus.expires_at else None,
                "status": bonus.status,
                "description": bonus.description,
                "created_at": bonus.created_at.isoformat(),
            })

        # Calculate summary stats
        active_bonuses = bonuses.filter(status=Bonus.BonusStatus.ACTIVE)
        available_bonuses = bonuses.filter(status=Bonus.BonusStatus.PENDING)
        bonus_balance = active_bonuses.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            "bonuses": data,
            "stats": {
                "active_count": active_bonuses.count(),
                "available_count": available_bonuses.count(),
                "bonus_balance": str(bonus_balance),
            }
        })


# =============================================================================
# PROMO CODE VIEWS
# =============================================================================

class PromoCodeListView(APIView):
    """GET /api/promo-codes/ — list active promo codes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import PromoCodeSerializer
        promo_codes = PromoCode.objects.filter(is_active=True)
        
        # Filter out expired codes
        now = timezone.now()
        promo_codes = promo_codes.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
        
        # Filter out codes that have reached max uses (if max_uses > 0)
        promo_codes = promo_codes.filter(
            models.Q(max_uses=0) | models.Q(uses_count__lt=models.F('max_uses'))
        )
        
        serializer = PromoCodeSerializer(promo_codes, many=True)
        return Response(serializer.data)


class RedeemPromoCodeView(APIView):
    """POST /api/bonuses/redeem-promo/ — redeem a promo code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip().upper()
        user = request.user

        if not code:
            return Response(
                {'error': 'Promo code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the promo code
        try:
            promo = PromoCode.objects.get(code__iexact=code)
        except PromoCode.DoesNotExist:
            return Response(
                {'error': 'Invalid promo code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if active
        if not promo.is_active:
            return Response(
                {'error': 'This promo code is no longer active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check expiration
        if promo.expires_at and promo.expires_at < timezone.now():
            return Response(
                {'error': 'This promo code has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check max uses
        if promo.max_uses > 0 and promo.uses_count >= promo.max_uses:
            return Response(
                {'error': 'This promo code has reached its maximum uses'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already redeemed this code
        if PromoCodeRedemption.objects.filter(user=user, promo_code=promo).exists():
            return Response(
                {'error': 'You have already redeemed this promo code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the bonus
        bonus = Bonus.objects.create(
            user=user,
            name=promo.name or f"Promo: {promo.code}",
            type=promo.bonus_type,
            amount=promo.bonus_amount,
            wagering=promo.bonus_amount * promo.wagering_requirement,
            status=Bonus.BonusStatus.ACTIVE,
            description=f"Redeemed from promo code: {promo.code}",
        )

        # Record redemption
        PromoCodeRedemption.objects.create(
            user=user,
            promo_code=promo,
            bonus=bonus,
        )

        # Increment uses count
        promo.uses_count += 1
        promo.save()

        return Response({
            'message': f'Promo code {promo.code} redeemed successfully!',
            'bonus': {
                'id': bonus.id,
                'name': bonus.name,
                'amount': str(bonus.amount),
                'type': bonus.type,
                'status': bonus.status,
            }
        })


class ClaimBonusView(APIView):
    """POST /api/bonuses/<pk>/claim/ — claim a pending bonus."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .serializers import BonusSerializer
        
        try:
            bonus = Bonus.objects.get(pk=pk, user=request.user)
        except Bonus.DoesNotExist:
            return Response(
                {'error': 'Bonus not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if bonus.status != 'pending':
            return Response(
                {'error': f'Cannot claim bonus with status: {bonus.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if bonus has expired
        if bonus.expires_at and bonus.expires_at < timezone.now():
            bonus.status = 'expired'
            bonus.save()
            return Response(
                {'error': 'This bonus has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Claim the bonus
        bonus.status = 'active'
        bonus.save()

        serializer = BonusSerializer(bonus)
        return Response({
            'message': 'Bonus claimed successfully!',
            'bonus': serializer.data
        })


# =============================================================================
# USER REFERRALS VIEW
# =============================================================================

class UserReferralsView(APIView):
    """GET /api/referrals/my — get current user's referral information."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get user's referral code
        referral_code = user.referral_code or ""

        # Get referrals made by this user
        referrals = Referral.objects.filter(referrer=user).select_related('referred_user').order_by('-created_at')

        referrals_data = []
        for ref in referrals:
            referrals_data.append({
                "id": str(ref.pk),
                "name": ref.name or (ref.referred_user.username if ref.referred_user else "Unknown"),
                "email": ref.email or (ref.referred_user.email if ref.referred_user else ""),
                "status": ref.status,
                "joined_at": ref.joined_at.isoformat() if ref.joined_at else None,
                "earnings": str(ref.earnings),
                "total_bets": str(ref.total_bets),
                "created_at": ref.created_at.isoformat(),
            })

        # Calculate stats
        total_referrals = referrals.count()
        active_referrals = referrals.filter(status=Referral.ReferralStatus.ACTIVE).count()
        total_earnings = referrals.aggregate(total=Sum('earnings'))['total'] or Decimal('0')
        total_bets_from_referrals = referrals.aggregate(total=Sum('total_bets'))['total'] or Decimal('0')

        return Response({
            "referral_code": referral_code,
            "referral_link": f"https://karnalix.com/register?ref={referral_code}",
            "referrals": referrals_data,
            "stats": {
                "total_referrals": total_referrals,
                "active_referrals": active_referrals,
                "total_earnings": str(total_earnings),
                "total_bets_from_referrals": str(total_bets_from_referrals),
            }
        })


# =============================================================================
# FAVORITES VIEW
# =============================================================================

class FavoritesView(APIView):
    """
    GET /api/favorites — get user's favorite games.
    POST /api/favorites — add a game to favorites.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = FavoriteGame.objects.filter(user=request.user).select_related(
            'game', 'game__category', 'game__provider'
        ).order_by('-created_at')

        data = []
        for fav in favorites:
            game = fav.game
            data.append({
                "id": str(game.pk),
                "slug": game.slug,
                "name": game.name,
                "image": game.image,
                "category": game.category.name if game.category else None,
                "category_slug": game.category.slug if game.category else None,
                "provider": game.provider.name if game.provider else None,
                "added_at": fav.created_at.isoformat(),
            })

        return Response(data)

    def post(self, request):
        game_id = request.data.get('game_id')
        game_slug = request.data.get('game_slug')

        if not game_id and not game_slug:
            return Response(
                {"detail": "game_id or game_slug is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if game_id:
                game = Game.objects.get(pk=game_id)
            else:
                game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return Response({"detail": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if already favorited
        if FavoriteGame.objects.filter(user=request.user, game=game).exists():
            return Response(
                {"detail": "Game already in favorites."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        FavoriteGame.objects.create(user=request.user, game=game)

        return Response({
            "detail": f"Added {game.name} to favorites.",
            "game_id": str(game.pk),
            "game_slug": game.slug,
        }, status=status.HTTP_201_CREATED)


class FavoriteDeleteView(APIView):
    """DELETE /api/favorites/<game_id> — remove game from favorites."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, game_id):
        try:
            # Try by ID first, then by slug
            if game_id.isdigit():
                fav = FavoriteGame.objects.get(user=request.user, game_id=int(game_id))
            else:
                fav = FavoriteGame.objects.get(user=request.user, game__slug=game_id)
        except FavoriteGame.DoesNotExist:
            return Response({"detail": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)

        game_name = fav.game.name
        fav.delete()

        return Response({"detail": f"Removed {game_name} from favorites."})


# =============================================================================
# USER SETTINGS API
# =============================================================================
class UserSettingsView(APIView):
    """
    GET /api/users/me/settings — get current user's settings.
    PUT /api/users/me/settings — update current user's settings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        
        return Response({
            "email_notifications": settings_obj.email_notifications,
            "push_notifications": settings_obj.push_notifications,
            "sms_notifications": settings_obj.sms_notifications,
            "promotional_emails": settings_obj.promotional_emails,
            "two_factor_auth": settings_obj.two_factor_auth,
            "biometric_login": settings_obj.biometric_login,
            "dark_mode": settings_obj.dark_mode,
            "language": settings_obj.language,
            "currency": settings_obj.currency,
            "timezone": settings_obj.timezone,
            "deposit_limit": str(settings_obj.deposit_limit) if settings_obj.deposit_limit else None,
            "session_limit": settings_obj.session_limit,
            "betting_limit": str(settings_obj.betting_limit) if settings_obj.betting_limit else None,
            "self_exclusion": settings_obj.self_exclusion,
        })

    def put(self, request):
        user = request.user
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        data = request.data

        # Update boolean fields
        bool_fields = [
            'email_notifications', 'push_notifications', 'sms_notifications',
            'promotional_emails', 'two_factor_auth', 'biometric_login',
            'dark_mode', 'self_exclusion'
        ]
        for field in bool_fields:
            if field in data:
                setattr(settings_obj, field, bool(data[field]))

        # Update string fields
        if 'language' in data:
            settings_obj.language = data['language']
        if 'currency' in data:
            settings_obj.currency = data['currency']
        if 'timezone' in data:
            settings_obj.timezone = data['timezone']

        # Update numeric fields
        if 'deposit_limit' in data:
            val = data['deposit_limit']
            settings_obj.deposit_limit = Decimal(val) if val else None
        if 'session_limit' in data:
            val = data['session_limit']
            settings_obj.session_limit = int(val) if val else None
        if 'betting_limit' in data:
            val = data['betting_limit']
            settings_obj.betting_limit = Decimal(val) if val else None

        settings_obj.save()

        return Response({
            "detail": "Settings updated successfully.",
            "email_notifications": settings_obj.email_notifications,
            "push_notifications": settings_obj.push_notifications,
            "sms_notifications": settings_obj.sms_notifications,
            "promotional_emails": settings_obj.promotional_emails,
            "two_factor_auth": settings_obj.two_factor_auth,
            "biometric_login": settings_obj.biometric_login,
            "dark_mode": settings_obj.dark_mode,
            "language": settings_obj.language,
            "currency": settings_obj.currency,
            "timezone": settings_obj.timezone,
            "deposit_limit": str(settings_obj.deposit_limit) if settings_obj.deposit_limit else None,
            "session_limit": settings_obj.session_limit,
            "betting_limit": str(settings_obj.betting_limit) if settings_obj.betting_limit else None,
            "self_exclusion": settings_obj.self_exclusion,
        })


# =============================================================================
# USER PASSWORD CHANGE
# =============================================================================
class UserPasswordChangeView(APIView):
    """
    POST /api/users/me/password/ — change current user's password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {'error': 'Both current_password and new_password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'New password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password changed successfully'})


# =============================================================================
# PUBLIC APIs (No Authentication Required)
# =============================================================================
class TestimonialListView(APIView):
    """GET /api/public/testimonials — list active testimonials."""
    permission_classes = [AllowAny]

    def get(self, request):
        testimonials = Testimonial.objects.filter(is_active=True).order_by('sort_order', '-created_at')[:10]
        data = []
        for t in testimonials:
            data.append({
                "id": t.pk,
                "name": t.name,
                "avatar": t.avatar or t.name[:2].upper() if t.name else "??",
                "location": t.location,
                "game": t.game,
                "amount": f"₹{int(t.amount):,}" if t.amount else "₹0",
                "message": t.message,
                "rating": t.rating,
            })
        return Response(data)


class LiveWinsView(APIView):
    """GET /api/public/live-wins — recent bet wins for live wins display."""
    permission_classes = [AllowAny]

    def get(self, request):
        # Get recent won bets with user info
        recent_wins = Bet.objects.filter(
            status=Bet.BetStatus.WON,
            win_amount__gt=0
        ).select_related('user', 'game').order_by('-settled_at', '-updated_at')[:20]

        data = []
        for bet in recent_wins:
            # Mask the username for privacy (e.g., "Ra***sh")
            username = bet.user.username or "User"
            if len(username) > 3:
                masked = username[:2] + "***" + username[-2:]
            else:
                masked = username[:1] + "***"

            # Calculate time ago
            time_diff = timezone.now() - (bet.settled_at or bet.updated_at)
            minutes = int(time_diff.total_seconds() / 60)
            if minutes < 60:
                time_ago = f"{minutes} min ago"
            elif minutes < 1440:
                time_ago = f"{minutes // 60} hour{'s' if minutes // 60 > 1 else ''} ago"
            else:
                time_ago = f"{minutes // 1440} day{'s' if minutes // 1440 > 1 else ''} ago"

            data.append({
                "user": masked,
                "game": bet.game_name or (bet.game.name if bet.game else "Unknown"),
                "amount": f"₹{int(bet.win_amount):,}",
                "time": time_ago,
            })

        return Response(data)


class PlatformStatsView(APIView):
    """GET /api/public/stats — platform statistics for homepage."""
    permission_classes = [AllowAny]

    def get(self, request):
        # Active players count
        active_players = User.objects.filter(is_active=True).count()

        # Total games count
        total_games = Game.objects.filter(is_active=True).count()

        # Total winnings (sum of all won bets)
        total_winnings = Bet.objects.filter(status=Bet.BetStatus.WON).aggregate(
            total=Sum('win_amount')
        )['total'] or 0

        # Format totals
        def format_large_number(num):
            if num >= 10000000:  # 1 crore
                return f"₹{num / 10000000:.1f}Cr+"
            elif num >= 100000:  # 1 lakh
                return f"₹{num / 100000:.1f}L+"
            elif num >= 1000:
                return f"₹{num / 1000:.1f}K+"
            return f"₹{int(num)}"

        def format_count(num):
            if num >= 1000:
                return f"{num // 1000}K+"
            return str(num)

        return Response({
            "active_players": format_count(active_players),
            "active_players_raw": active_players,
            "total_games": f"{total_games}+",
            "total_games_raw": total_games,
            "total_winnings": format_large_number(float(total_winnings)),
            "total_winnings_raw": str(total_winnings),
            "instant_payouts": "24/7",
        })


class ReferralTierListView(APIView):
    """GET /api/config/referral-tiers — list referral tier requirements."""
    permission_classes = [AllowAny]

    def get(self, request):
        tiers = ReferralTier.objects.all().order_by('level')
        data = []
        for tier in tiers:
            data.append({
                "level": tier.level,
                "referrals": tier.referrals_required,
                "bonus": f"₹{int(tier.bonus_amount):,}",
                "perReferral": f"₹{int(tier.per_referral_amount):,}",
            })
        return Response(data)


# =============================================================================
# ROLE-SPECIFIC VIEWS - PowerHouse, SuperAdmin, Master
# =============================================================================

from .permissions import (
    IsPowerHouse, IsSuperAdminOrAbove, IsMasterOrAbove,
    can_create_role, get_manageable_roles, log_audit_action
)
from .models import AuditLog


def _create_audit_log(admin_user, action, entity_type, entity_id, payload=None, request=None):
    """Helper to create audit log entries."""
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    AuditLog.objects.create(
        admin_user=admin_user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=payload or {},
        ip_address=ip_address,
    )


# =============================================================================
# POWERHOUSE VIEWS
# =============================================================================

class PowerHouseDashboardStatsView(APIView):
    """GET /api/powerhouse/stats — global platform statistics for PowerHouse."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def get(self, request):
        # User statistics by role
        users_by_role = {
            'powerhouse': User.objects.filter(role=User.Role.POWERHOUSE).count(),
            'super_admin': User.objects.filter(role=User.Role.SUPER_ADMIN).count(),
            'master': User.objects.filter(role=User.Role.MASTER).count(),
            'user': User.objects.filter(role=User.Role.USER).count(),
        }
        
        total_users = sum(users_by_role.values())
        active_users = User.objects.filter(status=User.Status.ACTIVE).count()
        suspended_users = User.objects.filter(status=User.Status.SUSPENDED).count()
        
        # Financial statistics
        total_wallet_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        total_deposits = DepositRequest.objects.filter(
            status=DepositRequest.DepositStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0
        total_withdrawals = WithdrawalRequest.objects.filter(
            status=WithdrawalRequest.WithdrawalStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Betting statistics
        total_bets = Bet.objects.count()
        total_bet_volume = Bet.objects.aggregate(total=Sum('bet_amount'))['total'] or 0
        total_wins_paid = Bet.objects.filter(status=Bet.BetStatus.WON).aggregate(
            total=Sum('win_amount')
        )['total'] or 0
        
        # Platform status
        platform_suspended = SystemConfig.objects.filter(
            key='platform_suspended', value='true'
        ).exists()
        
        return Response({
            'users': {
                'total': total_users,
                'by_role': users_by_role,
                'active': active_users,
                'suspended': suspended_users,
            },
            'finances': {
                'total_wallet_balance': str(total_wallet_balance),
                'total_deposits': str(total_deposits),
                'total_withdrawals': str(total_withdrawals),
                'net_deposits': str(total_deposits - total_withdrawals),
            },
            'betting': {
                'total_bets': total_bets,
                'total_volume': str(total_bet_volume),
                'total_wins_paid': str(total_wins_paid),
                'house_edge': str(total_bet_volume - total_wins_paid) if total_bet_volume else '0',
            },
            'platform': {
                'is_suspended': platform_suspended,
            },
        })


class PowerHouseCreateSuperAdminView(APIView):
    """POST /api/powerhouse/superadmins — create a SuperAdmin."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def post(self, request):
        data = request.data
        email = (data.get('email') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        full_name = (data.get('full_name') or '').strip()
        transfer_limit = data.get('transfer_limit')

        if not username or not email or not password:
            return Response(
                {"detail": "username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        user = User(
            username=username,
            email=email,
            name=full_name or username,
            role=User.Role.SUPER_ADMIN,
            referral_code=referral_code,
            parent=request.user,
            created_by=request.user,
            transfer_limit=Decimal(str(transfer_limit)) if transfer_limit else None,
        )
        user.set_password(password)
        user.save()

        Wallet.objects.get_or_create(user=user, defaults={"balance": 0, "currency": "INR"})
        UserSettings.objects.get_or_create(user=user)

        _create_audit_log(
            request.user, 'create_superadmin', 'user', user.pk,
            {'username': username, 'email': email}, request
        )

        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class PowerHouseSuperAdminListView(APIView):
    """GET /api/powerhouse/superadmins — list all SuperAdmins."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def get(self, request):
        superadmins = User.objects.filter(role=User.Role.SUPER_ADMIN).order_by('-date_joined')
        data = []
        for u in superadmins:
            wallet = Wallet.objects.filter(user=u).first()
            data.append({
                **_user_payload(u),
                'wallet_balance': str(wallet.balance) if wallet else '0',
                'transfer_limit': str(u.transfer_limit) if u.transfer_limit else None,
                'created_at': u.date_joined.isoformat(),
                'status': u.status,
                'masters_count': User.objects.filter(
                    role=User.Role.MASTER, parent=u
                ).count(),
            })
        return Response(data)


class PowerHouseMintCoinsView(APIView):
    """POST /api/powerhouse/mint — mint coins (root level coin generation)."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def post(self, request):
        data = request.data
        to_user_id = data.get('to_user_id')
        amount = data.get('amount')
        description = data.get('description', 'PowerHouse mint')

        if not to_user_id or not amount:
            return Response(
                {"detail": "to_user_id and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            to_user = User.objects.get(pk=to_user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            return Response(
                {"detail": "Amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(
                user=to_user, defaults={"balance": 0, "currency": "INR"}
            )
            wallet.balance += amount_decimal
            wallet.save()

            Transaction.objects.create(
                user=to_user,
                type=Transaction.TransactionType.BONUS,
                amount=amount_decimal,
                method='powerhouse_mint',
                reference=description,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        _create_audit_log(
            request.user, 'mint_coins', 'wallet', to_user.pk,
            {'amount': str(amount_decimal), 'to_user': to_user.username, 'description': description},
            request
        )

        return Response({
            "detail": f"Minted {amount} coins to {to_user.username}.",
            "new_balance": str(wallet.balance),
        })


class PowerHouseEmergencySuspendView(APIView):
    """POST /api/powerhouse/emergency-suspend — toggle platform suspension."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def post(self, request):
        suspend = request.data.get('suspend', True)
        
        config, created = SystemConfig.objects.update_or_create(
            key='platform_suspended',
            defaults={
                'value': 'true' if suspend else 'false',
                'updated_by': request.user,
            }
        )

        _create_audit_log(
            request.user, 'emergency_suspend' if suspend else 'emergency_resume',
            'platform', 'system',
            {'suspended': suspend}, request
        )

        return Response({
            "detail": f"Platform {'suspended' if suspend else 'resumed'}.",
            "is_suspended": suspend,
        })


class PowerHouseAuditLogsView(APIView):
    """GET /api/powerhouse/audit-logs — view all audit logs."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def get(self, request):
        action_filter = request.query_params.get('action', '').strip()
        entity_type_filter = request.query_params.get('entity_type', '').strip()
        user_id_filter = request.query_params.get('user_id', '').strip()
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))

        qs = AuditLog.objects.select_related('admin_user').order_by('-created_at')

        if action_filter:
            qs = qs.filter(action__icontains=action_filter)
        if entity_type_filter:
            qs = qs.filter(entity_type=entity_type_filter)
        if user_id_filter:
            qs = qs.filter(admin_user_id=user_id_filter)

        total_count = qs.count()
        logs = qs[offset:offset + limit]

        data = []
        for log in logs:
            data.append({
                'id': log.pk,
                'admin_user': log.admin_user.username if log.admin_user else None,
                'admin_user_id': log.admin_user_id,
                'action': log.action,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'payload': log.payload,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
            })

        return Response({
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'logs': data,
        })


class PowerHouseGlobalWalletsView(APIView):
    """GET /api/powerhouse/global-wallets — view all wallet balances."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def get(self, request):
        role_filter = request.query_params.get('role', '').strip()
        min_balance = request.query_params.get('min_balance', '').strip()
        
        qs = Wallet.objects.select_related('user').order_by('-balance')
        
        if role_filter:
            qs = qs.filter(user__role=role_filter)
        if min_balance:
            qs = qs.filter(balance__gte=Decimal(min_balance))

        data = []
        for wallet in qs[:500]:  # Limit to 500 results
            data.append({
                'user_id': wallet.user.pk,
                'username': wallet.user.username,
                'role': wallet.user.role,
                'balance': str(wallet.balance),
                'currency': wallet.currency,
                'status': wallet.user.status,
            })

        # Aggregate stats
        total_balance = qs.aggregate(total=Sum('balance'))['total'] or 0
        
        return Response({
            'total_balance': str(total_balance),
            'wallet_count': qs.count(),
            'wallets': data,
        })


class PowerHouseSuspendUserView(APIView):
    """POST /api/powerhouse/users/<id>/suspend — suspend any user."""
    permission_classes = [IsAuthenticated, IsPowerHouse]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.role == User.Role.POWERHOUSE:
            return Response(
                {"detail": "Cannot suspend a PowerHouse user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suspend = request.data.get('suspend', True)
        user.status = User.Status.SUSPENDED if suspend else User.Status.ACTIVE
        user.is_active = not suspend
        user.save()

        _create_audit_log(
            request.user, 'suspend_user' if suspend else 'activate_user',
            'user', user.pk,
            {'username': user.username, 'suspended': suspend}, request
        )

        return Response({
            "detail": f"User {user.username} {'suspended' if suspend else 'activated'}.",
            "status": user.status,
        })


# =============================================================================
# SUPERADMIN VIEWS
# =============================================================================

class SuperAdminDashboardStatsView(APIView):
    """GET /api/superadmin/stats — dashboard stats for SuperAdmin."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def get(self, request):
        # Masters and users under this SuperAdmin (or all if PowerHouse)
        if request.user.role == User.Role.POWERHOUSE:
            masters = User.objects.filter(role=User.Role.MASTER)
            users = User.objects.filter(role=User.Role.USER)
        else:
            masters = User.objects.filter(
                role=User.Role.MASTER,
                parent=request.user
            )
            # Users under these masters
            master_ids = list(masters.values_list('id', flat=True))
            users = User.objects.filter(
                role=User.Role.USER,
                assigned_master_id__in=master_ids
            )

        # Financial stats
        user_ids = list(users.values_list('id', flat=True))
        total_user_balance = Wallet.objects.filter(
            user_id__in=user_ids
        ).aggregate(total=Sum('balance'))['total'] or 0

        pending_withdrawals = WithdrawalRequest.objects.filter(
            user_id__in=user_ids,
            status=WithdrawalRequest.WithdrawalStatus.PENDING
        )
        pending_deposits = DepositRequest.objects.filter(
            user_id__in=user_ids,
            status=DepositRequest.DepositStatus.PENDING
        )

        return Response({
            'masters': {
                'total': masters.count(),
                'active': masters.filter(status=User.Status.ACTIVE).count(),
                'suspended': masters.filter(status=User.Status.SUSPENDED).count(),
            },
            'users': {
                'total': users.count(),
                'active': users.filter(status=User.Status.ACTIVE).count(),
                'suspended': users.filter(status=User.Status.SUSPENDED).count(),
            },
            'finances': {
                'total_user_balance': str(total_user_balance),
                'pending_withdrawals_count': pending_withdrawals.count(),
                'pending_withdrawals_amount': str(
                    pending_withdrawals.aggregate(total=Sum('amount'))['total'] or 0
                ),
                'pending_deposits_count': pending_deposits.count(),
            },
        })


class SuperAdminCreateMasterView(APIView):
    """POST /api/superadmin/masters — create a Master."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def post(self, request):
        data = request.data
        email = (data.get('email') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        full_name = (data.get('full_name') or '').strip()
        transfer_limit = data.get('transfer_limit')

        if not username or not email or not password:
            return Response(
                {"detail": "username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        user = User(
            username=username,
            email=email,
            name=full_name or username,
            role=User.Role.MASTER,
            referral_code=referral_code,
            parent=request.user,
            created_by=request.user,
            transfer_limit=Decimal(str(transfer_limit)) if transfer_limit else None,
        )
        user.set_password(password)
        user.save()

        Wallet.objects.get_or_create(user=user, defaults={"balance": 0, "currency": "INR"})
        UserSettings.objects.get_or_create(user=user)

        _create_audit_log(
            request.user, 'create_master', 'user', user.pk,
            {'username': username, 'email': email}, request
        )

        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class SuperAdminMasterListView(APIView):
    """GET /api/superadmin/masters — list Masters."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def get(self, request):
        if request.user.role == User.Role.POWERHOUSE:
            masters = User.objects.filter(role=User.Role.MASTER)
        else:
            masters = User.objects.filter(role=User.Role.MASTER, parent=request.user)

        data = []
        for u in masters.order_by('-date_joined'):
            wallet = Wallet.objects.filter(user=u).first()
            users_count = User.objects.filter(
                role=User.Role.USER,
                assigned_master=u
            ).count()
            data.append({
                **_user_payload(u),
                'wallet_balance': str(wallet.balance) if wallet else '0',
                'transfer_limit': str(u.transfer_limit) if u.transfer_limit else None,
                'created_at': u.date_joined.isoformat(),
                'status': u.status,
                'users_count': users_count,
            })
        return Response(data)


class SuperAdminSetMasterLimitsView(APIView):
    """PATCH /api/superadmin/masters/<id>/limits — set Master's transfer limit."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def patch(self, request, pk):
        try:
            master = User.objects.get(pk=pk, role=User.Role.MASTER)
        except User.DoesNotExist:
            return Response({"detail": "Master not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure SuperAdmin can only manage their own Masters
        if request.user.role == User.Role.SUPER_ADMIN and master.parent != request.user:
            return Response(
                {"detail": "You can only manage Masters you created."},
                status=status.HTTP_403_FORBIDDEN,
            )

        transfer_limit = request.data.get('transfer_limit')
        if transfer_limit is not None:
            master.transfer_limit = Decimal(str(transfer_limit)) if transfer_limit else None
            master.save()

        _create_audit_log(
            request.user, 'set_master_limits', 'user', master.pk,
            {'transfer_limit': str(transfer_limit)}, request
        )

        return Response({
            "detail": "Master limits updated.",
            "transfer_limit": str(master.transfer_limit) if master.transfer_limit else None,
        })


class SuperAdminSuspendMasterView(APIView):
    """POST /api/superadmin/masters/<id>/suspend — suspend/activate a Master."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def post(self, request, pk):
        try:
            master = User.objects.get(pk=pk, role=User.Role.MASTER)
        except User.DoesNotExist:
            return Response({"detail": "Master not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure SuperAdmin can only manage their own Masters
        if request.user.role == User.Role.SUPER_ADMIN and master.parent != request.user:
            return Response(
                {"detail": "You can only manage Masters you created."},
                status=status.HTTP_403_FORBIDDEN,
            )

        suspend = request.data.get('suspend', True)
        master.status = User.Status.SUSPENDED if suspend else User.Status.ACTIVE
        master.is_active = not suspend
        master.save()

        _create_audit_log(
            request.user, 'suspend_master' if suspend else 'activate_master',
            'user', master.pk,
            {'username': master.username, 'suspended': suspend}, request
        )

        return Response({
            "detail": f"Master {master.username} {'suspended' if suspend else 'activated'}.",
            "status": master.status,
        })


class SuperAdminTransferCoinsView(APIView):
    """POST /api/superadmin/transfer — transfer coins (within limit)."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def post(self, request):
        data = request.data
        to_user_id = data.get('to_user_id')
        amount = data.get('amount')
        description = data.get('description', 'SuperAdmin transfer')

        if not to_user_id or not amount:
            return Response(
                {"detail": "to_user_id and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            to_user = User.objects.get(pk=to_user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        amount_decimal = Decimal(str(amount))
        
        # Check transfer limit (PowerHouse has no limit)
        if request.user.role != User.Role.POWERHOUSE:
            if request.user.transfer_limit and amount_decimal > request.user.transfer_limit:
                return Response(
                    {"detail": f"Amount exceeds your transfer limit of {request.user.transfer_limit}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Check sender's wallet
        sender_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, defaults={"balance": 0, "currency": "INR"}
        )
        if sender_wallet.balance < amount_decimal:
            return Response(
                {"detail": "Insufficient balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            sender_wallet.balance -= amount_decimal
            sender_wallet.save()

            receiver_wallet, _ = Wallet.objects.get_or_create(
                user=to_user, defaults={"balance": 0, "currency": "INR"}
            )
            receiver_wallet.balance += amount_decimal
            receiver_wallet.save()

            ref = f"TRF-{uuid.uuid4().hex[:8].upper()}"
            Transaction.objects.create(
                user=request.user,
                type=Transaction.TransactionType.TRANSFER,
                amount=-amount_decimal,
                method='superadmin_transfer_out',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )
            Transaction.objects.create(
                user=to_user,
                type=Transaction.TransactionType.TRANSFER,
                amount=amount_decimal,
                method='superadmin_transfer_in',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        _create_audit_log(
            request.user, 'transfer_coins', 'wallet', to_user.pk,
            {'amount': str(amount_decimal), 'to_user': to_user.username}, request
        )

        return Response({
            "detail": f"Transferred {amount} coins to {to_user.username}.",
            "new_balance": str(sender_wallet.balance),
        })


class SuperAdminReportsView(APIView):
    """GET /api/superadmin/reports — platform reports."""
    permission_classes = [IsAuthenticated, IsSuperAdminOrAbove]

    def get(self, request):
        report_type = request.query_params.get('type', 'summary')
        
        # Get date range
        from datetime import timedelta
        today = timezone.now().date()
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if start_date_str:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = today - timedelta(days=30)
        
        if end_date_str:
            from datetime import datetime
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = today

        # Filter users based on role
        if request.user.role == User.Role.POWERHOUSE:
            user_filter = {}
        else:
            master_ids = User.objects.filter(
                role=User.Role.MASTER, parent=request.user
            ).values_list('id', flat=True)
            user_filter = {'user__assigned_master_id__in': master_ids}

        # Deposits report
        deposits = DepositRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            **user_filter
        ).aggregate(
            total_amount=Sum('amount'),
            approved_amount=Sum('amount', filter=Q(status=DepositRequest.DepositStatus.APPROVED)),
            count=Count('id'),
            approved_count=Count('id', filter=Q(status=DepositRequest.DepositStatus.APPROVED)),
        )

        # Withdrawals report
        withdrawals = WithdrawalRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            **user_filter
        ).aggregate(
            total_amount=Sum('amount'),
            approved_amount=Sum('amount', filter=Q(status=WithdrawalRequest.WithdrawalStatus.APPROVED)),
            count=Count('id'),
            approved_count=Count('id', filter=Q(status=WithdrawalRequest.WithdrawalStatus.APPROVED)),
        )

        # Bets report
        bets = Bet.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            **user_filter
        ).aggregate(
            total_volume=Sum('bet_amount'),
            total_wins=Sum('win_amount'),
            count=Count('id'),
            won_count=Count('id', filter=Q(status=Bet.BetStatus.WON)),
            lost_count=Count('id', filter=Q(status=Bet.BetStatus.LOST)),
        )

        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'deposits': {
                'total_amount': str(deposits['total_amount'] or 0),
                'approved_amount': str(deposits['approved_amount'] or 0),
                'count': deposits['count'],
                'approved_count': deposits['approved_count'],
            },
            'withdrawals': {
                'total_amount': str(withdrawals['total_amount'] or 0),
                'approved_amount': str(withdrawals['approved_amount'] or 0),
                'count': withdrawals['count'],
                'approved_count': withdrawals['approved_count'],
            },
            'bets': {
                'total_volume': str(bets['total_volume'] or 0),
                'total_wins': str(bets['total_wins'] or 0),
                'count': bets['count'],
                'won_count': bets['won_count'],
                'lost_count': bets['lost_count'],
            },
        })


# =============================================================================
# MASTER VIEWS
# =============================================================================

class MasterDashboardStatsView(APIView):
    """GET /api/master/stats — dashboard stats for Master."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def get(self, request):
        # Get users under this Master
        if request.user.role in [User.Role.POWERHOUSE, User.Role.SUPER_ADMIN]:
            users = User.objects.filter(role=User.Role.USER)
        else:
            users = User.objects.filter(
                role=User.Role.USER,
                assigned_master=request.user
            )

        user_ids = list(users.values_list('id', flat=True))
        
        # Financial stats
        total_user_balance = Wallet.objects.filter(
            user_id__in=user_ids
        ).aggregate(total=Sum('balance'))['total'] or 0

        # Today's activity
        today = timezone.now().date()
        today_bets = Bet.objects.filter(
            user_id__in=user_ids,
            created_at__date=today
        ).aggregate(
            volume=Sum('bet_amount'),
            count=Count('id'),
        )

        today_deposits = DepositRequest.objects.filter(
            user_id__in=user_ids,
            created_at__date=today,
            status=DepositRequest.DepositStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_withdrawals = WithdrawalRequest.objects.filter(
            user_id__in=user_ids,
            created_at__date=today,
            status=WithdrawalRequest.WithdrawalStatus.APPROVED
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'users': {
                'total': users.count(),
                'active': users.filter(status=User.Status.ACTIVE).count(),
                'suspended': users.filter(status=User.Status.SUSPENDED).count(),
            },
            'finances': {
                'total_user_balance': str(total_user_balance),
            },
            'today': {
                'bet_volume': str(today_bets['volume'] or 0),
                'bet_count': today_bets['count'],
                'deposits': str(today_deposits),
                'withdrawals': str(today_withdrawals),
            },
        })


class MasterCreateUserView(APIView):
    """POST /api/master/users — create a User."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def post(self, request):
        data = request.data
        email = (data.get('email') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        full_name = (data.get('full_name') or '').strip()
        betting_limit = data.get('betting_limit')

        if not username or not email or not password:
            return Response(
                {"detail": "username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"detail": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        referral_code = uuid.uuid4().hex[:8].upper()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = uuid.uuid4().hex[:8].upper()

        user = User(
            username=username,
            email=email,
            name=full_name or username,
            role=User.Role.USER,
            referral_code=referral_code,
            parent=request.user,
            created_by=request.user,
            assigned_master=request.user if request.user.role == User.Role.MASTER else None,
            betting_limit=Decimal(str(betting_limit)) if betting_limit else None,
        )
        user.set_password(password)
        user.save()

        Wallet.objects.get_or_create(user=user, defaults={"balance": 0, "currency": "INR"})
        UserSettings.objects.get_or_create(user=user)

        _create_audit_log(
            request.user, 'create_user', 'user', user.pk,
            {'username': username, 'email': email}, request
        )

        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class MasterUserListView(APIView):
    """GET /api/master/users — list Users under this Master."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def get(self, request):
        if request.user.role in [User.Role.POWERHOUSE, User.Role.SUPER_ADMIN]:
            users = User.objects.filter(role=User.Role.USER)
        else:
            users = User.objects.filter(
                role=User.Role.USER,
                assigned_master=request.user
            )

        search = request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(name__icontains=search)
            )

        data = []
        for u in users.order_by('-date_joined'):
            wallet = Wallet.objects.filter(user=u).first()
            data.append({
                **_user_payload(u),
                'wallet_balance': str(wallet.balance) if wallet else '0',
                'betting_limit': str(u.betting_limit) if u.betting_limit else None,
                'created_at': u.date_joined.isoformat(),
                'status': u.status,
            })
        return Response(data)


class MasterSuspendUserView(APIView):
    """POST /api/master/users/<id>/suspend — suspend/activate a User."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only manage Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        suspend = request.data.get('suspend', True)
        user.status = User.Status.SUSPENDED if suspend else User.Status.ACTIVE
        user.is_active = not suspend
        user.save()

        _create_audit_log(
            request.user, 'suspend_user' if suspend else 'activate_user',
            'user', user.pk,
            {'username': user.username, 'suspended': suspend}, request
        )

        return Response({
            "detail": f"User {user.username} {'suspended' if suspend else 'activated'}.",
            "status": user.status,
        })


class MasterResetUserPasswordView(APIView):
    """PATCH /api/master/users/<id>/password — reset User's password."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only manage Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_password = request.data.get('new_password')
        if not new_password or len(new_password) < 6:
            return Response(
                {"detail": "Password must be at least 6 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        _create_audit_log(
            request.user, 'reset_password', 'user', user.pk,
            {'username': user.username}, request
        )

        return Response({"detail": f"Password reset for {user.username}."})


class MasterSetUserBettingLimitView(APIView):
    """PATCH /api/master/users/<id>/betting-limit — set User's betting limit."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only manage Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        betting_limit = request.data.get('betting_limit')
        user.betting_limit = Decimal(str(betting_limit)) if betting_limit else None
        user.save()

        _create_audit_log(
            request.user, 'set_betting_limit', 'user', user.pk,
            {'username': user.username, 'betting_limit': str(betting_limit)}, request
        )

        return Response({
            "detail": "Betting limit updated.",
            "betting_limit": str(user.betting_limit) if user.betting_limit else None,
        })


class MasterDepositForUserView(APIView):
    """POST /api/master/users/<id>/deposit — deposit coins for a User."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only manage Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        amount = request.data.get('amount')
        description = request.data.get('description', 'Master deposit')

        if not amount:
            return Response(
                {"detail": "Amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            return Response(
                {"detail": "Amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check Master's transfer limit
        if request.user.role == User.Role.MASTER:
            if request.user.transfer_limit and amount_decimal > request.user.transfer_limit:
                return Response(
                    {"detail": f"Amount exceeds your transfer limit of {request.user.transfer_limit}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check Master's wallet balance
            master_wallet, _ = Wallet.objects.get_or_create(
                user=request.user, defaults={"balance": 0, "currency": "INR"}
            )
            if master_wallet.balance < amount_decimal:
                return Response(
                    {"detail": "Insufficient balance in your wallet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with db_transaction.atomic():
            # Deduct from Master's wallet (if Master role)
            if request.user.role == User.Role.MASTER:
                master_wallet.balance -= amount_decimal
                master_wallet.save()

            # Add to User's wallet
            user_wallet, _ = Wallet.objects.get_or_create(
                user=user, defaults={"balance": 0, "currency": "INR"}
            )
            user_wallet.balance += amount_decimal
            user_wallet.save()

            ref = f"MDEP-{uuid.uuid4().hex[:8].upper()}"
            
            if request.user.role == User.Role.MASTER:
                Transaction.objects.create(
                    user=request.user,
                    type=Transaction.TransactionType.TRANSFER,
                    amount=-amount_decimal,
                    method='master_deposit_out',
                    reference=ref,
                    status=Transaction.TransactionStatus.COMPLETED,
                )
            
            Transaction.objects.create(
                user=user,
                type=Transaction.TransactionType.DEPOSIT,
                amount=amount_decimal,
                method='master_deposit',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )

        _create_audit_log(
            request.user, 'deposit_for_user', 'wallet', user.pk,
            {'username': user.username, 'amount': str(amount_decimal)}, request
        )

        return Response({
            "detail": f"Deposited {amount} to {user.username}.",
            "user_balance": str(user_wallet.balance),
        })


class MasterWithdrawForUserView(APIView):
    """POST /api/master/users/<id>/withdraw — withdraw coins for a User."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only manage Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        amount = request.data.get('amount')
        description = request.data.get('description', 'Master withdrawal')

        if not amount:
            return Response(
                {"detail": "Amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            return Response(
                {"detail": "Amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check User's wallet balance
        user_wallet, _ = Wallet.objects.get_or_create(
            user=user, defaults={"balance": 0, "currency": "INR"}
        )
        if user_wallet.balance < amount_decimal:
            return Response(
                {"detail": "User has insufficient balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            # Deduct from User's wallet
            user_wallet.balance -= amount_decimal
            user_wallet.save()

            # Add to Master's wallet (if Master role)
            if request.user.role == User.Role.MASTER:
                master_wallet, _ = Wallet.objects.get_or_create(
                    user=request.user, defaults={"balance": 0, "currency": "INR"}
                )
                master_wallet.balance += amount_decimal
                master_wallet.save()

            ref = f"MWTH-{uuid.uuid4().hex[:8].upper()}"
            
            Transaction.objects.create(
                user=user,
                type=Transaction.TransactionType.WITHDRAWAL,
                amount=-amount_decimal,
                method='master_withdrawal',
                reference=ref,
                status=Transaction.TransactionStatus.COMPLETED,
            )
            
            if request.user.role == User.Role.MASTER:
                Transaction.objects.create(
                    user=request.user,
                    type=Transaction.TransactionType.TRANSFER,
                    amount=amount_decimal,
                    method='master_withdrawal_in',
                    reference=ref,
                    status=Transaction.TransactionStatus.COMPLETED,
                )

        _create_audit_log(
            request.user, 'withdraw_for_user', 'wallet', user.pk,
            {'username': user.username, 'amount': str(amount_decimal)}, request
        )

        return Response({
            "detail": f"Withdrew {amount} from {user.username}.",
            "user_balance": str(user_wallet.balance),
        })


class MasterUserBetHistoryView(APIView):
    """GET /api/master/users/<id>/bets — view User's bet history."""
    permission_classes = [IsAuthenticated, IsMasterOrAbove]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.USER)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permission
        if request.user.role == User.Role.MASTER and user.assigned_master != request.user:
            return Response(
                {"detail": "You can only view bets for Users assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        status_filter = request.query_params.get('status', '').strip()

        bets = Bet.objects.filter(user=user).order_by('-bet_at')
        if status_filter:
            bets = bets.filter(status=status_filter)

        total = bets.count()
        bets = bets[offset:offset + limit]

        data = []
        for bet in bets:
            data.append({
                'id': bet.pk,
                'game_name': bet.game_name,
                'game_type': bet.game_type,
                'category': bet.category,
                'bet_amount': str(bet.bet_amount),
                'win_amount': str(bet.win_amount),
                'odds': str(bet.odds) if bet.odds else None,
                'status': bet.status,
                'bet_at': bet.bet_at.isoformat(),
            })

        return Response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'bets': data,
        })
