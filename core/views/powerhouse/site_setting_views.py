import json
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


def _parse_promo_banners(value):
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def site_setting_update(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first() or SiteSetting()
    data = request.data

    # Accept multipart/form-data for logo file upload
    if request.FILES.get('logo'):
        data = {
            'name': request.data.get('name') or '',
            'phones': [x for x in [request.data.get('phone1'), request.data.get('phone2')] if x],
            'emails': [x for x in [request.data.get('email1')] if x],
            'whatsapp_number': request.data.get('whatsapp_number') or '',
            'hero_title': request.data.get('hero_title') or '',
            'hero_subtitle': request.data.get('hero_subtitle') or '',
            'footer_description': request.data.get('footer_description') or '',
            'promo_banners': _parse_promo_banners(request.data.get('promo_banners')),
            'logo': request.FILES.get('logo'),
        }

    ser = SiteSettingSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
