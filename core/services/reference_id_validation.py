"""Global uniqueness for non-empty transaction/reference IDs across Deposit and Withdraw."""
from django.db.models.functions import Lower

from core.models import Deposit, Withdraw


REF_TAKEN_MSG = "This transaction/reference id is already used."


def validation_error_response(exc):
    """Map Django ValidationError to DRF Response (400)."""
    from rest_framework.response import Response
    from rest_framework import status as http_status

    d = getattr(exc, "message_dict", None) or getattr(exc, "error_dict", None)
    if d:
        return Response(d, status=http_status.HTTP_400_BAD_REQUEST)
    messages = getattr(exc, "messages", None)
    if messages:
        return Response({"detail": list(messages)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)


def normalize_reference_id(value):
    if value is None:
        return ""
    return str(value).strip()


def validate_reference_id_unique(
    value,
    *,
    exclude_deposit_id=None,
    exclude_withdraw_id=None,
):
    """
    If value is non-empty after strip, ensure no other Deposit or Withdraw has the same
    reference (case-insensitive).
    Raises django.core.exceptions.ValidationError with REF_TAKEN_MSG on conflict.
    """
    from django.core.exceptions import ValidationError

    ref = normalize_reference_id(value)
    if not ref:
        return

    ref_lower = ref.lower()

    dep_qs = Deposit.objects.annotate(_rlower=Lower("reference_id")).filter(_rlower=ref_lower)
    if exclude_deposit_id is not None:
        dep_qs = dep_qs.exclude(pk=exclude_deposit_id)
    if dep_qs.exists():
        raise ValidationError({"reference_id": REF_TAKEN_MSG})

    wd_qs = Withdraw.objects.annotate(_rlower=Lower("reference_id")).filter(_rlower=ref_lower)
    if exclude_withdraw_id is not None:
        wd_qs = wd_qs.exclude(pk=exclude_withdraw_id)
    if wd_qs.exists():
        raise ValidationError({"reference_id": REF_TAKEN_MSG})
