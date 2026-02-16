from django.urls import path
from core.views.player import (
    dashboard_views,
    player_views,
    kyc_views,
    deposit_withdraw_views,
    profile_views,
    message_views,
    transfer_views,
)

urlpatterns = [
    path('dashboard/', dashboard_views.dashboard),
    path('wallet/', player_views.wallet),
    path('transactions/', player_views.transaction_list),
    path('game-log/', player_views.game_log_list),
    path('deposit-payment-modes/', player_views.deposit_payment_modes),
    path('payment-modes/', player_views.payment_mode_list_create),
    path('payment-modes/<int:pk>/', player_views.payment_mode_detail),
    path('kyc/', kyc_views.kyc_status),
    path('kyc/submit/', kyc_views.kyc_submit),
    path('deposit-request/', deposit_withdraw_views.deposit_request),
    path('withdraw-request/', deposit_withdraw_views.withdraw_request),
    path('profile/', profile_views.profile_get),
    path('profile/update/', profile_views.profile_update),
    path('change-password/', profile_views.change_password),
    path('messages/', message_views.message_list),
    path('messages/send/', message_views.message_create),
    path('transfer/', transfer_views.transfer),
]
