from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from core.permissions import require_role
from core.models import GameLog, UserRole
from core.serializers import GameLogSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_log_list(request):
    err = require_role(request, [UserRole.SUPER])
    if err:
        return err
    qs = GameLog.objects.filter(
        Q(user__parent=request.user) | Q(user__parent__parent=request.user)
    ).select_related('user', 'game', 'provider').order_by('-created_at')[:500]
    return Response(GameLogSerializer(qs, many=True).data)
