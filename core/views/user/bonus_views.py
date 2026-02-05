"""
User bonuses - GET list of bonuses for current user; POST apply promo code.
"""
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from core.models import Bonus, BonusRule
from core.serializers.financial_serializers import BonusSerializer
from core.permissions import user_required


# Map BonusRule.bonus_type to Bonus.bonus_type (Bonus has no DEPOSIT, use MANUAL)
BONUS_TYPE_MAP = {
    'WELCOME': Bonus.BonusType.WELCOME,
    'DEPOSIT': Bonus.BonusType.MANUAL,
    'CASHBACK': Bonus.BonusType.CASHBACK,
    'REFERRAL': Bonus.BonusType.REFERRAL,
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def bonus_list(request):
    """
    List bonuses for the current user.
    """
    queryset = Bonus.objects.filter(user=request.user).order_by('-created_at')
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    serializer = BonusSerializer(page_obj, many=True)
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_required
def apply_promo(request):
    """
    Apply a promo code: find active BonusRule by promo_code, validate dates, create Bonus for user.
    Body: { "code": "KARNA100" }
    """
    code = (request.data.get('code') or '').strip().upper()
    if not code:
        return Response({'error': 'Promo code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rule = BonusRule.objects.get(promo_code__iexact=code, is_active=True)
    except BonusRule.DoesNotExist:
        return Response({'error': 'Invalid or inactive promo code'}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    if rule.valid_from and now < rule.valid_from:
        return Response({'error': 'This offer is not yet valid'}, status=status.HTTP_400_BAD_REQUEST)
    if rule.valid_until and now > rule.valid_until:
        return Response({'error': 'This offer has expired'}, status=status.HTTP_400_BAD_REQUEST)

    amount = rule.max_bonus or Decimal('0')
    if amount <= 0:
        return Response({'error': 'This offer has no bonus amount'}, status=status.HTTP_400_BAD_REQUEST)

    bonus_type = BONUS_TYPE_MAP.get(rule.bonus_type, Bonus.BonusType.MANUAL)
    rollover = (amount * rule.rollover_multiplier) if rule.rollover_multiplier else Decimal('0')

    bonus = Bonus.objects.create(
        user=request.user,
        bonus_type=bonus_type,
        amount=amount,
        rollover_requirement=rollover,
        status=Bonus.Status.AVAILABLE,
        granted_by=None,
    )
    serializer = BonusSerializer(bonus)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_required
def claim_bonus(request, bonus_id):
    """
    Claim an available bonus: set status from AVAILABLE to ACTIVE.
    """
    try:
        bonus = Bonus.objects.get(id=bonus_id, user=request.user)
    except Bonus.DoesNotExist:
        return Response({'error': 'Bonus not found'}, status=status.HTTP_404_NOT_FOUND)
    if bonus.status != Bonus.Status.AVAILABLE:
        return Response({'error': 'Bonus is not available to claim'}, status=status.HTTP_400_BAD_REQUEST)
    bonus.status = Bonus.Status.ACTIVE
    bonus.save(update_fields=['status'])
    serializer = BonusSerializer(bonus)
    return Response(serializer.data)
