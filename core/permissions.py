"""
Role-based permission classes and decorators for KarnaliX.
Hierarchy: POWERHOUSE → SUPER → MASTER → USER
"""
from functools import wraps
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status


# =============================================================================
# PERMISSION CLASSES (for class-based views)
# =============================================================================

class IsPowerhouse(BasePermission):
    """Only POWERHOUSE role can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'POWERHOUSE'


class IsSuper(BasePermission):
    """POWERHOUSE and SUPER roles can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['POWERHOUSE', 'SUPER']


class IsMaster(BasePermission):
    """POWERHOUSE, SUPER, and MASTER roles can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['POWERHOUSE', 'SUPER', 'MASTER']


class IsUser(BasePermission):
    """Any authenticated user can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated


# =============================================================================
# PERMISSION DECORATORS (for function-based views)
# =============================================================================

def powerhouse_required(view_func):
    """Decorator: Only POWERHOUSE role can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if request.user.role != 'POWERHOUSE':
            return Response(
                {'error': 'Powerhouse access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def super_required(view_func):
    """Decorator: POWERHOUSE and SUPER roles can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if request.user.role not in ['POWERHOUSE', 'SUPER']:
            return Response(
                {'error': 'Super or higher access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def master_required(view_func):
    """Decorator: POWERHOUSE, SUPER, and MASTER roles can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if request.user.role not in ['POWERHOUSE', 'SUPER', 'MASTER']:
            return Response(
                {'error': 'Master or higher access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def user_required(view_func):
    """Decorator: Any authenticated user can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_hierarchy(user):
    """Get all users in the hierarchy under the given user."""
    from core.models import User
    
    if user.role == 'POWERHOUSE':
        return User.objects.all()
    elif user.role == 'SUPER':
        # Get masters and users under this super
        return User.objects.filter(parent=user) | User.objects.filter(parent__parent=user)
    elif user.role == 'MASTER':
        # Get users under this master
        return User.objects.filter(parent=user)
    else:
        # Regular users can only see themselves
        return User.objects.filter(id=user.id)


def can_manage_user(manager, target_user):
    """Check if manager can manage target_user based on hierarchy."""
    if manager.role == 'POWERHOUSE':
        return True
    elif manager.role == 'SUPER':
        return target_user.role in ['MASTER', 'USER'] and (
            target_user.parent == manager or target_user.parent and target_user.parent.parent == manager
        )
    elif manager.role == 'MASTER':
        return target_user.role == 'USER' and target_user.parent == manager
    return False


def get_allowed_child_roles(user_role):
    """Get roles that can be created by a given role."""
    role_map = {
        'POWERHOUSE': ['SUPER', 'MASTER', 'USER'],
        'SUPER': ['MASTER', 'USER'],
        'MASTER': ['USER'],
        'USER': [],
    }
    return role_map.get(user_role, [])
