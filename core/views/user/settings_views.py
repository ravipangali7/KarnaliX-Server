"""
User (role USER) settings - GET/PATCH preferences (notifications, theme, etc.).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.permissions import user_required


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@user_required
def user_settings(request):
    """
    GET: Return current user's settings JSON.
    PATCH: Merge request body into user.settings and save.
    """
    user = request.user
    if not hasattr(user, 'settings'):
        user.settings = {}
        user.save(update_fields=['settings'])

    if request.method == 'GET':
        return Response(user.settings if user.settings else {})

    elif request.method == 'PATCH':
        if not isinstance(request.data, dict):
            return Response({'error': 'Expected JSON object'}, status=status.HTTP_400_BAD_REQUEST)
        current = dict(user.settings) if user.settings else {}
        current.update(request.data)
        user.settings = current
        user.save(update_fields=['settings'])
        return Response(user.settings)
