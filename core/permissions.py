"""
Role-based permission classes and decorators for the multi-tier admin system.

Role Hierarchy (highest to lowest):
- POWERHOUSE (4): Platform owner with absolute authority
- SUPER_ADMIN (3): Platform management
- MASTER (2): Agent/Operator who manages users
- USER (1): Player/End user
"""

from functools import wraps
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status

from .models import User, SystemConfig


# Role hierarchy levels
ROLE_HIERARCHY = {
    'powerhouse': 4,
    'super_admin': 3,
    'master': 2,
    'user': 1,
}


def get_role_level(role):
    """Get the hierarchy level for a role."""
    return ROLE_HIERARCHY.get(role, 0)


def is_platform_suspended():
    """Check if platform is in emergency suspend mode."""
    try:
        config = SystemConfig.objects.filter(key='platform_suspended').first()
        return config and config.value.lower() == 'true'
    except Exception:
        return False


class IsPowerHouse(permissions.BasePermission):
    """Permission class for PowerHouse-only access."""
    message = "Only PowerHouse users can access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role == User.Role.POWERHOUSE


class IsSuperAdminOrAbove(permissions.BasePermission):
    """Permission class for SuperAdmin or PowerHouse access."""
    message = "Only SuperAdmin or PowerHouse users can access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in [User.Role.SUPER_ADMIN, User.Role.POWERHOUSE]


class IsMasterOrAbove(permissions.BasePermission):
    """Permission class for Master, SuperAdmin, or PowerHouse access."""
    message = "Only Master, SuperAdmin, or PowerHouse users can access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in [User.Role.MASTER, User.Role.SUPER_ADMIN, User.Role.POWERHOUSE]


class IsActiveUser(permissions.BasePermission):
    """Permission class to check if user is active (not suspended)."""
    message = "Your account has been suspended."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.status == User.Status.ACTIVE and request.user.is_active


class PlatformNotSuspended(permissions.BasePermission):
    """Permission class to check if platform is not in emergency suspend mode."""
    message = "Platform is currently suspended for maintenance."

    def has_permission(self, request, view):
        # PowerHouse can always access even during suspension
        if request.user.is_authenticated and request.user.role == User.Role.POWERHOUSE:
            return True
        return not is_platform_suspended()


class CanManageUser(permissions.BasePermission):
    """Permission class to check if the requesting user can manage a target user."""
    message = "You don't have permission to manage this user."

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Can't manage yourself
        if request.user.pk == obj.pk:
            return False
        
        # Check role hierarchy
        return request.user.can_manage(obj)


def require_role(*allowed_roles):
    """
    Decorator for view methods to restrict access by role.
    
    Usage:
        @require_role('powerhouse', 'super_admin')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentication required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if request.user.role not in allowed_roles:
                return Response(
                    {"detail": f"Access restricted to: {', '.join(allowed_roles)}"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_min_role(min_role):
    """
    Decorator for view methods to restrict access by minimum role level.
    
    Usage:
        @require_min_role('master')  # Allows master, super_admin, powerhouse
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentication required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            min_level = get_role_level(min_role)
            user_level = get_role_level(request.user.role)
            
            if user_level < min_level:
                return Response(
                    {"detail": f"Minimum role required: {min_role}"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_audit_action(action, entity_type, get_entity_id=None):
    """
    Decorator to automatically log audit actions.
    
    Usage:
        @log_audit_action('create', 'user', lambda req, res: res.data.get('id'))
        def create_user(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            from .models import AuditLog
            
            response = view_func(self, request, *args, **kwargs)
            
            # Only log successful actions
            if response.status_code in [200, 201]:
                entity_id = ''
                if get_entity_id:
                    try:
                        entity_id = str(get_entity_id(request, response))
                    except Exception:
                        entity_id = ''
                elif 'pk' in kwargs:
                    entity_id = str(kwargs['pk'])
                
                # Get client IP
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0].strip()
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                
                AuditLog.objects.create(
                    admin_user=request.user if request.user.is_authenticated else None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    payload={
                        'method': request.method,
                        'path': request.path,
                        'data': dict(request.data) if hasattr(request, 'data') else {},
                    },
                    ip_address=ip_address,
                )
            
            return response
        return wrapper
    return decorator


class RoleBasedPermission(permissions.BasePermission):
    """
    Dynamic permission class that checks role hierarchy.
    
    Usage in views:
        permission_classes = [RoleBasedPermission]
        required_role = 'super_admin'  # Or set dynamically
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        required_role = getattr(view, 'required_role', 'user')
        required_level = get_role_level(required_role)
        user_level = get_role_level(request.user.role)
        
        return user_level >= required_level


def can_create_role(creator_role, target_role):
    """
    Check if a user with creator_role can create a user with target_role.
    
    Rules:
    - PowerHouse can create SuperAdmin, Master, User
    - SuperAdmin can create Master, User
    - Master can create User only
    - User cannot create anyone
    """
    creation_rules = {
        'powerhouse': ['super_admin', 'master', 'user'],
        'super_admin': ['master', 'user'],
        'master': ['user'],
        'user': [],
    }
    
    allowed_roles = creation_rules.get(creator_role, [])
    return target_role in allowed_roles


def get_manageable_roles(user_role):
    """Get list of roles that a user can manage."""
    role_management = {
        'powerhouse': ['super_admin', 'master', 'user'],
        'super_admin': ['master', 'user'],
        'master': ['user'],
        'user': [],
    }
    return role_management.get(user_role, [])


def get_viewable_roles(user_role):
    """Get list of roles that a user can view."""
    if user_role == 'powerhouse':
        return ['powerhouse', 'super_admin', 'master', 'user']
    elif user_role == 'super_admin':
        return ['super_admin', 'master', 'user']
    elif user_role == 'master':
        return ['master', 'user']
    return ['user']
