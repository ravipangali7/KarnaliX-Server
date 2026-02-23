"""
Public games: GameCategory list, GameProvider list, Game list and detail (by category filter).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import GameCategory, GameProvider, Game
from core.serializers import (
    GameCategorySerializer,
    GameProviderSerializer,
    GameListSerializer,
    GameDetailSerializer,
    ComingSoonGameSerializer,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """GET game categories (active)."""
    qs = GameCategory.objects.filter(is_active=True)
    serializer = GameCategorySerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def provider_list(request):
    """GET game providers (active)."""
    qs = GameProvider.objects.filter(is_active=True)
    serializer = GameProviderSerializer(qs, many=True)
    return Response(serializer.data)


def _paginate_queryset(qs, request, page_size=24):
    """Paginate queryset; return (page_queryset, count, next_page, prev_page)."""
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = max(1, min(100, int(request.query_params.get('page_size', page_size))))
    except (ValueError, TypeError):
        page_size = 24
    count = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    page_qs = qs[start:end]
    next_page = page + 1 if end < count else None
    previous_page = page - 1 if page > 1 else None
    return page_qs, count, next_page, previous_page


@api_view(['GET'])
@permission_classes([AllowAny])
def game_list(request):
    """GET games (active). Optional query: category_id, provider_id, page, page_size."""
    qs = Game.objects.filter(is_active=True).select_related('category', 'provider').order_by('id')
    category_id = request.query_params.get('category_id') or request.query_params.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)
    provider_id = request.query_params.get('provider_id') or request.query_params.get('provider')
    if provider_id:
        qs = qs.filter(provider_id=provider_id)
    page_qs, count, next_page, previous_page = _paginate_queryset(qs, request, page_size=24)
    serializer = GameListSerializer(page_qs, many=True)
    base = request.build_absolute_uri(request.path)
    next_url = None
    prev_url = None
    if next_page is not None:
        p = request.GET.copy()
        p['page'] = next_page
        next_url = f"{base}?{p.urlencode()}"
    if previous_page is not None:
        p = request.GET.copy()
        p['page'] = previous_page
        prev_url = f"{base}?{p.urlencode()}"
    return Response({
        'count': count,
        'next': next_url,
        'previous': prev_url,
        'results': serializer.data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def coming_soon_list(request):
    """GET games marked as coming soon (active + is_coming_soon=True)."""
    qs = Game.objects.filter(is_active=True, is_coming_soon=True).select_related('category', 'provider').order_by('id')
    serializer = ComingSoonGameSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def game_detail(request, pk):
    """GET single game by id."""
    obj = Game.objects.filter(pk=pk, is_active=True).select_related('category', 'provider').first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = GameDetailSerializer(obj)
    return Response(serializer.data)
