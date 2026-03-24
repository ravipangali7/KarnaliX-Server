"""Powerhouse: Withdraw list, detail, approve/reject, withdraw_direct."""
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from core.permissions import require_role
from core.models import Withdraw, User, UserRole
from core.serializers import WithdrawSerializer
from core.services.withdraw_service import approve_withdraw
from core.services.reference_id_validation import validate_reference_id_unique, validation_error_response, normalize_reference_id
from django.core.exceptions import ValidationError as DjangoValidationError


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_direct(request):
    """Verify PIN first; then create and approve withdrawal. No withdrawal created if PIN is invalid."""
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    pin = request.data.get('pin')
    password = request.data.get('password')
    if pin is not None and pin != '':
        if not request.user.pin or request.user.pin != pin:
            return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    elif password is not None and password != '':
        if not request.user.check_password(password):
            return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'detail': 'PIN or password required.'}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.data.get('user_id')
    amount_raw = request.data.get('amount')
    remarks = request.data.get('remarks', '') or ''
    reference_id = request.data.get('reference_id', '') or ''
    if not normalize_reference_id(reference_id):
        return Response({'detail': 'Transaction/reference id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if user_id is None:
        return Response({'detail': 'user_id required.'}, status=status.HTTP_400_BAD_REQUEST)
    if amount_raw is None:
        return Response({'detail': 'amount required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount_raw))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    if not User.objects.filter(pk=user_id, role__in=[UserRole.SUPER, UserRole.MASTER, UserRole.PLAYER]).exists():
        return Response({'detail': 'User not found or not allowed.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        validate_reference_id_unique(reference_id)
    except DjangoValidationError as e:
        return validation_error_response(e)

    wd = Withdraw.objects.create(
        user_id=user_id, amount=amount, remarks=remarks, reference_id=reference_id.strip(), status='pending'
    )
    ok, msg = approve_withdraw(wd, request.user)
    if not ok:
        wd.delete()
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(WithdrawSerializer(wd, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def withdraw_list(request):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    qs = Withdraw.objects.all().select_related('user', 'payment_mode', 'processed_by').order_by('-created_at')
    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(Q(user__username__icontains=search) | Q(reference_id__icontains=search))
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return Response(WithdrawSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def withdraw_detail(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    obj = Withdraw.objects.filter(pk=pk).first()
    if not obj:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'PATCH':
        update_fields = []
        if 'amount' in request.data and obj.status == 'pending':
            try:
                new_amount = Decimal(str(request.data['amount']))
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
            if new_amount <= 0:
                return Response({'detail': 'Amount must be positive.'}, status=status.HTTP_400_BAD_REQUEST)
            obj.amount = new_amount
            update_fields.append('amount')
        if 'reference_id' in request.data:
            try:
                validate_reference_id_unique(
                    request.data.get('reference_id'),
                    exclude_withdraw_id=obj.pk,
                )
            except DjangoValidationError as e:
                return validation_error_response(e)
            obj.reference_id = request.data.get('reference_id') if request.data.get('reference_id') is not None else ''
            update_fields.append('reference_id')
        if 'remarks' in request.data:
            obj.remarks = request.data.get('remarks') if request.data.get('remarks') is not None else ''
            update_fields.append('remarks')
        if update_fields:
            obj.save(update_fields=update_fields)
        return Response(WithdrawSerializer(obj, context={'request': request}).data)
    return Response(WithdrawSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_approve(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    pin = request.data.get('pin')
    password = request.data.get('password')
    if pin is not None and pin != '':
        if not request.user.pin or request.user.pin != pin:
            return Response({'detail': 'Invalid PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    elif password is not None and password != '':
        if not request.user.check_password(password):
            return Response({'detail': 'Invalid password.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'detail': 'PIN or password required.'}, status=status.HTTP_400_BAD_REQUEST)
    wd = Withdraw.objects.filter(pk=pk, status='pending').first()
    if not wd:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    ok, msg = approve_withdraw(wd, request.user)
    if not ok:
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
    return Response(WithdrawSerializer(wd, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_reject(request, pk):
    err = require_role(request, [UserRole.POWERHOUSE])
    if err:
        return err
    wd = Withdraw.objects.filter(pk=pk, status='pending').first()
    if not wd:
        return Response({'detail': 'Not found or not pending.'}, status=status.HTTP_404_NOT_FOUND)
    wd.status = 'rejected'
    wd.reject_reason = request.data.get('reject_reason', '')
    wd.processed_by = request.user
    wd.processed_at = timezone.now()
    wd.save()
    return Response(WithdrawSerializer(wd, context={'request': request}).data)
