"""
Public site: SiteSetting (single), CMSPage by slug, Testimonials list.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import SiteSetting, CMSPage, Testimonial, SliderSlide, LiveBettingSection, Popup, PaymentMethod
from core.serializers import SiteSettingSerializer, CMSPageSerializer, TestimonialSerializer, SliderSlideSerializer, LiveBettingSectionSerializer, PopupSerializer, PaymentMethodSerializer


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
