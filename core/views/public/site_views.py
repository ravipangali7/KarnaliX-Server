"""
Public site: SiteSetting (single), CMSPage by slug, Testimonials list, second-home sections.
"""
import os
from django.conf import settings as django_settings
from django.http import HttpResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import SiteSetting, CMSPage, Testimonial, SliderSlide, LiveBettingSection, Popup, PaymentMethod, Country, Game, GameProvider, GameCategory
from core.serializers import SiteSettingSerializer, CMSPageSerializer, TestimonialSerializer, SliderSlideSerializer, LiveBettingSectionSerializer, PopupSerializer, PaymentMethodSerializer


def _get_og_meta(request):
    """Shared logic for og_image, og_title, og_description from SiteSetting."""
    site_domain = getattr(django_settings, 'SITE_DOMAIN', '').rstrip('/') or request.build_absolute_uri('/').rstrip('/')
    obj = SiteSetting.objects.first()
    if obj and obj.logo:
        og_image = request.build_absolute_uri(obj.logo.url)
    else:
        og_image = f"{site_domain}/karnali-logo.png"
    og_title = (obj.name.strip() if obj and getattr(obj, 'name', None) else None) or 'KarnaliX'
    og_description = (obj.footer_description.strip() if obj and getattr(obj, 'footer_description', None) else None) or ''
    return og_image, og_title, (og_description[:300] if og_description else '')


@api_view(['GET'])
@permission_classes([AllowAny])
def site_setting(request):
    """GET single site setting (hero, logo, footer, etc.)."""
    obj = SiteSetting.objects.first()
    if not obj:
        return Response({}, status=status.HTTP_200_OK)
    serializer = SiteSettingSerializer(obj)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def site_meta(request):
    """
    Open Graph / social meta for link previews (WhatsApp, Facebook, etc.).
    Crawlers do not run JavaScript, so they need meta in the initial HTML.
    Returns og_image (absolute URL), og_title, og_description for server-side injection.
    """
    og_image, og_title, og_description = _get_og_meta(request)
    return Response({
        'og_image': og_image,
        'og_title': og_title,
        'og_description': og_description,
    })


def serve_app_index(request):
    """
    Serve the frontend index.html with Open Graph meta injected from SiteSetting
    so WhatsApp/Facebook show the site logo in link previews.
    Set FRONTEND_INDEX_HTML_PATH in settings to the path to your built index.html
    (e.g. os.path.join(BASE_DIR, '../frontend/dist/index.html')).
    Then point your frontend root URL to this view (e.g. Nginx proxy_pass for / to this).
    """
    path = getattr(django_settings, 'FRONTEND_INDEX_HTML_PATH', None)
    if not path or not os.path.isfile(path):
        raise Http404('FRONTEND_INDEX_HTML_PATH not set or file not found')
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    og_image, og_title, og_description = _get_og_meta(request)
    default_logo = 'https://luckyuser365.com/karnali-logo.png'
    if default_logo in html:
        html = html.replace(default_logo, og_image)
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@api_view(['GET'])
@permission_classes([AllowAny])
def cms_pages_footer(request):
    """GET CMS pages for footer (is_footer=True, is_active=True)."""
    qs = CMSPage.objects.filter(is_footer=True, is_active=True)
    serializer = CMSPageSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def cms_page_by_slug(request, slug):
    """GET single CMS page by slug."""
    obj = CMSPage.objects.filter(slug=slug, is_active=True).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CMSPageSerializer(obj)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def testimonials_list(request):
    """GET testimonials for public (e.g. home page)."""
    qs = Testimonial.objects.all()
    serializer = TestimonialSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def slider_list(request):
    """GET slider slides for second home (ordered)."""
    qs = SliderSlide.objects.all()
    serializer = SliderSlideSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def live_betting_list(request):
    """GET live betting sections with events for second home."""
    qs = LiveBettingSection.objects.prefetch_related('events').all()
    serializer = LiveBettingSectionSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_methods_list(request):
    """GET active payment methods filtered/ordered by site_payments_accepted_json.payment_method_ids when set."""
    site = SiteSetting.objects.first()
    payments_json = (site.site_payments_accepted_json or {}) if site else {}
    payment_method_ids = payments_json.get('payment_method_ids') if isinstance(payments_json, dict) else None

    if payment_method_ids and isinstance(payment_method_ids, list) and len(payment_method_ids) > 0:
        # Fetch only the selected active methods and preserve the configured order
        id_list = [int(i) for i in payment_method_ids if isinstance(i, (int, float)) or (isinstance(i, str) and i.isdigit())]
        methods_by_id = {
            m.id: m
            for m in PaymentMethod.objects.filter(is_active=True, id__in=id_list)
        }
        ordered = [methods_by_id[i] for i in id_list if i in methods_by_id]
        serializer = PaymentMethodSerializer(ordered, many=True, context={'request': request})
    else:
        qs = PaymentMethod.objects.filter(is_active=True)
        serializer = PaymentMethodSerializer(qs, many=True, context={'request': request})

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def popup_list(request):
    """GET active popups for home page (is_active=True, ordered by order)."""
    qs = Popup.objects.filter(is_active=True).order_by('order', 'id')
    serializer = PopupSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def countries_list(request):
    """GET active countries for register/login country code dropdown (is_active=True, ordered by name)."""
    qs = Country.objects.filter(is_active=True).order_by('name')
    data = [
        {'id': c.id, 'name': c.name, 'country_code': c.country_code, 'currency_symbol': c.currency_symbol}
        for c in qs
    ]
    return Response(data)


def _build_media_url(request, path_or_url):
    """Return absolute URL for media file or pass-through for full URLs."""
    if not path_or_url or not str(path_or_url).strip():
        return None
    s = str(path_or_url).strip()
    if s.startswith(('http://', 'https://', 'data:', '<svg')):
        return s
    base = getattr(django_settings, 'MEDIA_URL', '/media/')
    if request:
        return request.build_absolute_uri(base + s.lstrip('/'))
    return (base + s).replace('//', '/')


def _game_image_url(request, game):
    """Preferred game image: coming_soon_image, then image, then image_url."""
    if game.coming_soon_image:
        return _build_media_url(request, game.coming_soon_image.name)
    if game.image:
        return _build_media_url(request, game.image.name)
    if game.image_url:
        return (game.image_url or '').strip() or None
    return None


def _provider_image_url(request, provider):
    if not provider or not provider.image:
        return None
    return _build_media_url(request, provider.image.name)


@api_view(['GET'])
@permission_classes([AllowAny])
def second_home_sections(request):
    """
    GET second home page sections (providers, top games, category-wise games, popular games)
    with exact names, full image URLs, and redirect links. Built from SiteSetting JSON only.
    Frontend can render response directly.
    """
    site = SiteSetting.objects.first()
    if not site:
        return Response({
            'providers': {'section_title': '', 'section_subtitle': '', 'section_svg': '', 'items': []},
            'top_games': {'section_title': '', 'section_svg': '', 'items': []},
            'categories_game': {'section_title': '', 'section_svg': '', 'categories': []},
            'popular_games': {'section_title': '', 'section_svg': '', 'items': []},
        })

    def parse_json(field, default=None):
        val = getattr(site, field, None) or {}
        if not isinstance(val, dict):
            return default or {}
        return val

    providers_json = parse_json('site_providers_json')
    top_games_json = parse_json('site_top_games_json')
    categories_game_json = parse_json('site_categories_game_json')
    popular_games_json = parse_json('site_popular_games_json')

    provider_ids = providers_json.get('provider_ids') if isinstance(providers_json.get('provider_ids'), list) else []
    top_game_ids = top_games_json.get('game_ids') if isinstance(top_games_json.get('game_ids'), list) else []
    popular_game_ids = popular_games_json.get('game_ids') if isinstance(popular_games_json.get('game_ids'), list) else []
    cat_entries = categories_game_json.get('categories') if isinstance(categories_game_json.get('categories'), list) else []

    # --- Providers: id, name, logo (2 letters), logo_image (full URL), link, single_game_id ---
    provider_cards = []
    if provider_ids:
        id_list = [int(x) for x in provider_ids if isinstance(x, (int, float)) or (isinstance(x, str) and str(x).isdigit())]
        providers_by_id = {p.id: p for p in GameProvider.objects.filter(is_active=True, id__in=id_list)}
        for pid in id_list:
            p = providers_by_id.get(pid)
            if not p:
                continue
            logo_image = _provider_image_url(request, p)
            single_game_id = None
            games_qs = Game.objects.filter(provider=p, is_active=True)
            if games_qs.count() == 1:
                single_game_id = games_qs.values_list('id', flat=True).first()
            elif games_qs.count() > 1:
                lobby = games_qs.filter(is_lobby=True).first()
                single_game_id = lobby.id if lobby else None
            if single_game_id:
                link = '/games/{}'.format(single_game_id)
            else:
                link = '/providers/{}'.format(p.id)
            provider_cards.append({
                'id': p.id,
                'name': p.name,
                'provider_code': getattr(p, 'code', '') or '',
                'logo': (p.code or p.name[:2].upper() if p.name else '')[:2],
                'logo_image': logo_image,
                'games': 0,
                'single_game_id': single_game_id,
                'link': link,
            })

    # --- Full game object: same shape as games list API + absolute image URL and link ---
    def game_card(game):
        cat = game.category
        prov = game.provider
        return {
            'id': game.id,
            'name': game.name,
            'game_uid': game.game_uid or '',
            'image': _game_image_url(request, game),
            'image_url': (game.image_url or '').strip() or None,
            'coming_soon_image': _build_media_url(request, game.coming_soon_image.name) if game.coming_soon_image else None,
            'min_bet': float(game.min_bet) if game.min_bet is not None else 0,
            'max_bet': float(game.max_bet) if game.max_bet is not None else 0,
            'category': game.category_id,
            'category_name': cat.name if cat else '',
            'provider': game.provider_id,
            'provider_name': prov.name if prov else '',
            'provider_code': prov.code if prov else '',
            'is_top_game': bool(game.is_top_game),
            'is_popular_game': bool(game.is_popular_game),
            'is_lobby': bool(game.is_lobby),
            'link': '/games/{}'.format(game.id),
        }

    all_game_ids = list(top_game_ids) + list(popular_game_ids)
    for entry in (cat_entries or []):
        gids = entry.get('game_ids') if isinstance(entry.get('game_ids'), list) else []
        all_game_ids.extend(gids)
    all_game_ids = list(dict.fromkeys(int(x) for x in all_game_ids if isinstance(x, (int, float)) or (isinstance(x, str) and str(x).isdigit())))
    games_by_id = {}
    if all_game_ids:
        for g in Game.objects.filter(is_active=True, id__in=all_game_ids).select_related('category', 'provider'):
            games_by_id[g.id] = g

    top_items = []
    for gid in top_game_ids:
        g = games_by_id.get(int(gid)) if str(gid).isdigit() or isinstance(gid, (int, float)) else None
        if g:
            top_items.append(game_card(g))

    popular_items = []
    for gid in popular_game_ids:
        g = games_by_id.get(int(gid)) if str(gid).isdigit() or isinstance(gid, (int, float)) else None
        if g:
            popular_items.append(game_card(g))

    # --- Category-wise: categories[] with category_id, section_title, section_icon, games[] ---
    categories_payload = []
    for entry in (cat_entries or []):
        cid = entry.get('category_id')
        gids = entry.get('game_ids') if isinstance(entry.get('game_ids'), list) else []
        section_title = entry.get('section_title') or ''
        section_icon = entry.get('section_icon') or ''
        games_list = []
        for gid in gids:
            g = games_by_id.get(int(gid)) if (isinstance(gid, (int, float)) or (isinstance(gid, str) and str(gid).isdigit())) else None
            if g:
                games_list.append(game_card(g))
        categories_payload.append({
            'category_id': cid,
            'section_title': section_title,
            'section_icon': section_icon,
            'games': games_list,
        })

    return Response({
        'providers': {
            'section_title': (providers_json.get('section_title') or '') or '',
            'section_subtitle': (providers_json.get('section_subtitle') or '') or '',
            'section_svg': (providers_json.get('section_svg') or '') or '',
            'items': provider_cards,
        },
        'top_games': {
            'section_title': (top_games_json.get('section_title') or '') or '',
            'section_svg': (top_games_json.get('section_svg') or '') or '',
            'items': top_items,
        },
        'categories_game': {
            'section_title': (categories_game_json.get('section_title') or '') or '',
            'section_svg': (categories_game_json.get('section_svg') or '') or '',
            'categories': categories_payload,
        },
        'popular_games': {
            'section_title': (popular_games_json.get('section_title') or '') or '',
            'section_svg': (popular_games_json.get('section_svg') or '') or '',
            'items': popular_items,
        },
    })
