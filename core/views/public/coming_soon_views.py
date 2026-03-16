"""Public: list active Coming Soon items for home page."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.models import ComingSoon
from core.serializers import ComingSoonSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def coming_soon_list(request):
    """GET active coming soon items, ordered by order then id."""
    qs = ComingSoon.objects.filter(is_active=True).order_by('order', 'id')
    serializer = ComingSoonSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)
