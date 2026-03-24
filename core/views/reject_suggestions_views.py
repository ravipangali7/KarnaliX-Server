"""Read-only reject-reason auto-suggestions from SuperSetting (for master/super/powerhouse)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import require_role
from core.models import SuperSetting, UserRole


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reject_reason_suggestions_list(request):
    err = require_role(request, [UserRole.MASTER, UserRole.SUPER, UserRole.POWERHOUSE])
    if err:
        return err
    s = SuperSetting.get_settings()
    raw = (getattr(s, "reject_reason_suggestions", None) if s else None) or {}
    if not isinstance(raw, dict):
        raw = {}
    data = raw.get("data")
    if not isinstance(data, list):
        data = []
    return Response({"data": data})
