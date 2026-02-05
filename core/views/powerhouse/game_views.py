"""
Powerhouse views for Game Provider and Game management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import GameProvider, Game
from core.serializers.game_serializers import (
    GameProviderSerializer, GameProviderCreateSerializer,
    GameSerializer, GameCreateSerializer
)
from core.permissions import powerhouse_required


# =============================================================================
# GAME PROVIDER VIEWS
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def provider_list_create(request):
    """
    GET: List all game providers
    POST: Create a new game provider
    """
    if request.method == 'GET':
        queryset = GameProvider.objects.all().order_by('name')
        
        # Filters
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(code__icontains=search)
        
        serializer = GameProviderSerializer(queryset, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = GameProviderCreateSerializer(data=request.data)
        if serializer.is_valid():
            provider = serializer.save()
            return Response(GameProviderSerializer(provider).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def provider_detail(request, provider_id):
    """
    GET: Get provider details
    PATCH: Update provider
    DELETE: Deactivate provider
    """
    try:
        provider = GameProvider.objects.get(id=provider_id)
    except GameProvider.DoesNotExist:
        return Response({'error': 'Provider not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = GameProviderSerializer(provider)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = GameProviderCreateSerializer(provider, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(GameProviderSerializer(provider).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        provider.status = 'INACTIVE'
        provider.save()
        return Response({'message': 'Provider deactivated'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def provider_toggle_status(request, provider_id):
    """Toggle provider status between ACTIVE and SUSPENDED."""
    try:
        provider = GameProvider.objects.get(id=provider_id)
    except GameProvider.DoesNotExist:
        return Response({'error': 'Provider not found'}, status=status.HTTP_404_NOT_FOUND)
    
    provider.status = 'SUSPENDED' if provider.status == 'ACTIVE' else 'ACTIVE'
    provider.save()
    
    return Response({
        'message': f'Provider {"suspended" if provider.status == "SUSPENDED" else "enabled"}',
        'status': provider.status
    })


# =============================================================================
# GAME VIEWS
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def game_list_create(request):
    """
    GET: List all games
    POST: Create a new game
    """
    if request.method == 'GET':
        queryset = Game.objects.all().order_by('name')
        
        # Filters
        status_filter = request.query_params.get('status')
        provider_id = request.query_params.get('provider_id')
        game_type = request.query_params.get('game_type')
        search = request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        if game_type:
            queryset = queryset.filter(game_type=game_type)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Pagination
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = GameSerializer(page_obj, many=True)
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    
    elif request.method == 'POST':
        serializer = GameCreateSerializer(data=request.data)
        if serializer.is_valid():
            game = serializer.save()
            return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def game_detail(request, game_id):
    """
    GET: Get game details
    PATCH: Update game
    DELETE: Disable game
    """
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = GameSerializer(game)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = GameCreateSerializer(game, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(GameSerializer(game).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        game.status = 'DISABLED'
        game.save()
        return Response({'message': 'Game disabled'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def game_toggle_status(request, game_id):
    """Toggle game status between ACTIVE and DISABLED."""
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return Response({'error': 'Game not found'}, status=status.HTTP_404_NOT_FOUND)
    
    game.status = 'DISABLED' if game.status == 'ACTIVE' else 'ACTIVE'
    game.save()
    
    return Response({
        'message': f'Game {"disabled" if game.status == "DISABLED" else "enabled"}',
        'status': game.status
    })
