"""
Public site: SiteSetting (single), CMSPage by slug, Testimonials list.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import SiteSetting, CMSPage, Testimonial, SliderSlide, LiveBettingSection
from core.serializers import SiteSettingSerializer, CMSPageSerializer, TestimonialSerializer, SliderSlideSerializer, LiveBettingSectionSerializer


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
