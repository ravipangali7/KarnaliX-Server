"""
Public (unauthenticated) views for website - games and providers.
"""
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import Game, GameProvider, SiteContent
from core.serializers.game_serializers import GameSerializer, GameProviderSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def public_game_list(request):
    """
    List active games. Optional query: category (game_type), provider_id, featured (limit).
    """
    queryset = Game.objects.filter(status='ACTIVE').select_related('provider').order_by('name')
    game_type = request.query_params.get('category') or request.query_params.get('game_type')
    provider_id = request.query_params.get('provider_id')
    featured = request.query_params.get('featured')
    if game_type:
        queryset = queryset.filter(game_type=game_type)
    if provider_id:
        queryset = queryset.filter(provider_id=provider_id)
    if featured:
        try:
            limit = int(featured)
            queryset = queryset[:limit]
        except ValueError:
            pass
    serializer = GameSerializer(queryset, many=True)
    return Response({'results': serializer.data, 'count': len(serializer.data)})


@api_view(['GET'])
@permission_classes([AllowAny])
def public_game_detail(request, game_id):
    """Get single game by id (active only)."""
    try:
        game = Game.objects.filter(status='ACTIVE').select_related('provider').get(id=game_id)
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = GameSerializer(game)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_provider_list(request):
    """List active game providers."""
    queryset = GameProvider.objects.filter(status='ACTIVE').order_by('name')
    serializer = GameProviderSerializer(queryset, many=True)
    return Response({'results': serializer.data, 'count': len(serializer.data)})


@api_view(['GET'])
@permission_classes([AllowAny])
def public_category_list(request):
    """
    List game categories with counts (active games grouped by game_type).
    Returns: { results: [ { game_type, label, slug, count }, ... ] }
    """
    counts = (
        Game.objects.filter(status='ACTIVE')
        .values('game_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Map backend game_type to frontend slug and label
    type_to_slug_label = {
        'CRASH': ('crash', 'Crash Games'),
        'CASINO': ('casino', 'Casino Games'),
        'SLOT': ('casino', 'Slots'),
        'LIVE': ('liveCasino', 'Live Casino'),
        'SPORTS': ('sports', 'Sports Betting'),
        'VIRTUAL': ('casual', 'Virtual Games'),
        'OTHER': ('casual', 'Other Games'),
    }
    seen_slugs = set()
    results = []
    for row in counts:
        game_type = row['game_type']
        slug, label = type_to_slug_label.get(game_type, ('casual', game_type.replace('_', ' ').title()))
        # Merge same slug (e.g. SLOT and CASINO both casino)
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            results.append({
                'game_type': game_type,
                'slug': slug,
                'label': label,
                'count': row['count'],
            })
        else:
            for r in results:
                if r['slug'] == slug:
                    r['count'] += row['count']
                    break
    return Response({'results': results, 'count': len(results)})


@api_view(['GET'])
@permission_classes([AllowAny])
def public_content(request):
    """
    Return all public website content: hero, promos, testimonials, recent_wins, coming_soon.
    Each key is null or empty array if not set; frontend falls back to static defaults.
    """
    keys = ['hero', 'promos', 'testimonials', 'recent_wins', 'coming_soon', 'faq', 'contact', 'terms', 'privacy',
            'about', 'careers', 'blog', 'guides', 'responsible_gaming', 'kyc', 'refunds', 'chat', 'referral_tiers']
    object_keys = ('hero', 'contact', 'terms', 'privacy', 'about', 'careers', 'blog', 'guides',
                   'responsible_gaming', 'kyc', 'refunds', 'chat')
    payload = {}
    for key in keys:
        try:
            row = SiteContent.objects.get(key=key)
            payload[key] = row.data if row.data is not None else ([] if key not in object_keys else (None if key == 'hero' else {}))
        except SiteContent.DoesNotExist:
            payload[key] = {} if key in object_keys and key != 'hero' else (None if key == 'hero' else [])
    return Response(payload)
