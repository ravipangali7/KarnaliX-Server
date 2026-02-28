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


def _parse_json_field(value, default=None):
    if default is None:
        default = []
    if value is None or value == '':
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _parse_positive_int(value):
    if value is None or value == '':
        return None
    try:
        n = int(value)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        from decimal import Decimal
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def _decimal_or_zero(value):
    from decimal import Decimal
    parsed = _parse_decimal(value)
    return parsed if parsed is not None else Decimal('0')


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def site_setting_update(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = SiteSetting.objects.first() or SiteSetting()
    data = request.data

    # Accept multipart/form-data for logo and favicon file upload
    if request.FILES.get('logo') or request.FILES.get('favicon'):
        data = {
            'name': request.data.get('name') or '',
            'phones': [x for x in [request.data.get('phone1'), request.data.get('phone2')] if x],
            'emails': [x for x in [request.data.get('email1')] if x],
            'whatsapp_number': request.data.get('whatsapp_number') or '',
            'hero_title': request.data.get('hero_title') or '',
            'hero_subtitle': request.data.get('hero_subtitle') or '',
            'footer_description': request.data.get('footer_description') or '',
            'promo_banners': _parse_promo_banners(request.data.get('promo_banners')),
            'active_players': _parse_positive_int(request.data.get('active_players')) or 0,
            'games_available': _parse_positive_int(request.data.get('games_available')) or 0,
            'total_winnings': _decimal_or_zero(request.data.get('total_winnings')),
            'instant_payouts': _parse_positive_int(request.data.get('instant_payouts')) or 0,
            'home_stats': _parse_json_field(request.data.get('home_stats'), []),
            'biggest_wins': _parse_json_field(request.data.get('biggest_wins'), []),
            'site_categories_json': _parse_json_field(request.data.get('site_categories_json'), {}),
            'site_top_games_json': _parse_json_field(request.data.get('site_top_games_json'), {}),
            'site_providers_json': _parse_json_field(request.data.get('site_providers_json'), {}),
            'site_categories_game_json': _parse_json_field(request.data.get('site_categories_game_json'), {}),
            'site_popular_games_json': _parse_json_field(request.data.get('site_popular_games_json'), {}),
            'site_coming_soon_json': _parse_json_field(request.data.get('site_coming_soon_json'), {}),
            'site_refer_bonus_json': _parse_json_field(request.data.get('site_refer_bonus_json'), {}),
            'site_payments_accepted_json': _parse_json_field(request.data.get('site_payments_accepted_json'), {}),
            'site_footer_json': _parse_json_field(request.data.get('site_footer_json'), {}),
            'site_welcome_deposit_json': _parse_json_field(request.data.get('site_welcome_deposit_json'), {}),
        }
        if request.FILES.get('logo'):
            data['logo'] = request.FILES.get('logo')
        if request.FILES.get('favicon'):
            data['favicon'] = request.FILES.get('favicon')

    ser = SiteSettingSerializer(obj, data=data, partial=(request.method == 'PATCH'))
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
