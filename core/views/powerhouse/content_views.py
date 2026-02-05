"""
Powerhouse views for SiteContent (website content: hero, promos, testimonials, coming_soon).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import SiteContent
from core.permissions import powerhouse_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def content_list(request):
    """
    GET: List all site content keys and their data (for Powerhouse dashboard).
    Returns: { results: [ { key, data, updated_at }, ... ] }
    """
    keys = ['hero', 'promos', 'testimonials', 'recent_wins', 'coming_soon', 'faq', 'contact', 'terms', 'privacy',
            'about', 'careers', 'blog', 'guides', 'responsible_gaming', 'kyc', 'refunds', 'chat', 'referral_tiers']
    results = []
    for key in keys:
        try:
            row = SiteContent.objects.get(key=key)
            results.append({
                'key': row.key,
                'data': row.data if row.data is not None else {},
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            })
        except SiteContent.DoesNotExist:
            results.append({
                'key': key,
                'data': {} if key != 'hero' else {},
                'updated_at': None,
            })
    return Response({'results': results})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def content_detail(request, key):
    """
    GET: Get site content for key.
    PATCH: Update data for key (body: { data: {...} }).
    """
    try:
        row = SiteContent.objects.get(key=key)
    except SiteContent.DoesNotExist:
        return Response({'error': 'Content key not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({
            'key': row.key,
            'data': row.data if row.data is not None else {},
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        })

    elif request.method == 'PATCH':
        if not isinstance(request.data, dict):
            return Response({'error': 'Expected JSON object'}, status=status.HTTP_400_BAD_REQUEST)
        # Accept either { data: {...} } or merge directly into row.data
        new_data = request.data.get('data')
        if new_data is not None:
            if not isinstance(new_data, (dict, list)):
                return Response({'error': 'data must be object or array'}, status=status.HTTP_400_BAD_REQUEST)
            row.data = new_data
        else:
            # Merge request.data (except key) into row.data
            current = dict(row.data) if isinstance(row.data, dict) else {}
            for k, v in request.data.items():
                if k != 'key' and k != 'updated_at':
                    current[k] = v
            row.data = current
        row.save(update_fields=['data', 'updated_at'])
        return Response({
            'key': row.key,
            'data': row.data,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        })
