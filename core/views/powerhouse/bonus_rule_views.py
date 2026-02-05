"""
Powerhouse views for BonusRule CRUD.
"""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import BonusRule
from core.serializers.financial_serializers import BonusRuleSerializer
from core.permissions import powerhouse_required


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def bonus_rule_list_create(request):
    """
    GET: List all bonus rules.
    POST: Create a new bonus rule.
    """
    if request.method == 'GET':
        queryset = BonusRule.objects.all().order_by('-created_at')
        serializer = BonusRuleSerializer(queryset, many=True)
        return Response({'results': serializer.data, 'count': len(serializer.data)})

    elif request.method == 'POST':
        data = request.data
        rule = BonusRule(
            name=data.get('name', ''),
            bonus_type=data.get('bonus_type', 'WELCOME'),
            percentage=Decimal(str(data.get('percentage', 0))),
            max_bonus=Decimal(str(data.get('max_bonus', 0))),
            min_deposit=Decimal(str(data.get('min_deposit', 0))),
            rollover_multiplier=Decimal(str(data.get('rollover_multiplier', 1))),
            is_active=data.get('is_active', True),
        )
        if data.get('valid_from'):
            from django.utils.dateparse import parse_datetime
            rule.valid_from = parse_datetime(data['valid_from'])
        if data.get('valid_until'):
            from django.utils.dateparse import parse_datetime
            rule.valid_until = parse_datetime(data['valid_until'])
        rule.save()
        return Response(BonusRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def bonus_rule_detail(request, rule_id):
    """
    GET: Get bonus rule by id.
    PATCH: Update bonus rule.
    DELETE: Delete bonus rule.
    """
    try:
        rule = BonusRule.objects.get(id=rule_id)
    except BonusRule.DoesNotExist:
        return Response({'error': 'Bonus rule not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(BonusRuleSerializer(rule).data)

    elif request.method == 'PATCH':
        data = request.data
        if 'name' in data:
            rule.name = data['name']
        if 'bonus_type' in data:
            rule.bonus_type = data['bonus_type']
        if 'percentage' in data:
            rule.percentage = Decimal(str(data['percentage']))
        if 'max_bonus' in data:
            rule.max_bonus = Decimal(str(data['max_bonus']))
        if 'min_deposit' in data:
            rule.min_deposit = Decimal(str(data['min_deposit']))
        if 'rollover_multiplier' in data:
            rule.rollover_multiplier = Decimal(str(data['rollover_multiplier']))
        if 'is_active' in data:
            rule.is_active = data['is_active']
        if 'valid_from' in data:
            from django.utils.dateparse import parse_datetime
            rule.valid_from = parse_datetime(data['valid_from']) if data['valid_from'] else None
        if 'valid_until' in data:
            from django.utils.dateparse import parse_datetime
            rule.valid_until = parse_datetime(data['valid_until']) if data['valid_until'] else None
        rule.save()
        return Response(BonusRuleSerializer(rule).data)

    elif request.method == 'DELETE':
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@powerhouse_required
def bonus_rule_toggle(request, rule_id):
    """Toggle is_active for a bonus rule."""
    try:
        rule = BonusRule.objects.get(id=rule_id)
    except BonusRule.DoesNotExist:
        return Response({'error': 'Bonus rule not found'}, status=status.HTTP_404_NOT_FOUND)
    rule.is_active = not rule.is_active
    rule.save()
    return Response({
        'message': f'Bonus rule {"activated" if rule.is_active else "deactivated"}',
        'is_active': rule.is_active,
    })
