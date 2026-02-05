"""
User referral - GET referral code and list of referred users.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import user_required


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_required
def referral(request):
    """
    Get current user referral code (username) and list of users they referred.
    """
    user = request.user
    referrals_qs = user.referrals.all().order_by('-created_at')
    referrals_list = [
        {
            'id': r.id,
            'username': r.username,
            'email': r.email or '',
            'joined_at': r.created_at,
            'status': r.status,
            'earnings': 0,
            'total_bets': 0,
        }
        for r in referrals_qs
    ]
    return Response({
        'referral_code': user.username,
        'referral_link': '/ref/' + user.username,
        'referrals': referrals_list,
        'count': len(referrals_list),
    })
