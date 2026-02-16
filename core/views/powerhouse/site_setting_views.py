from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.permissions import require_role
from core.models import SiteSetting, UserRole
from core.serializers import SiteSettingSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def site_setting_get(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first()
    return Response(SiteSettingSerializer(obj).data if obj else None)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def site_setting_update(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first() or SiteSetting()
    ser = SiteSettingSerializer(obj, data=request.data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
