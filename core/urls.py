"""
URL routing for KarnaliX API.
Organized by role: auth, powerhouse, super, master, user
"""
from django.urls import path

# Auth views
from core.views.auth_views import (
    login_view, register_view, me_view, logout_view,
    refresh_token_view, change_password_view,
    send_otp_view, verify_otp_view,
)

# Public views (unauthenticated)
from core.views import public_views as pub_views
from core.views import game_callback_views as game_callback_views

# Powerhouse views
from core.views.powerhouse import dashboard_views as ph_dashboard
from core.views.powerhouse import super_views as ph_super
from core.views.powerhouse import master_views as ph_master
from core.views.powerhouse import user_views as ph_user
from core.views.powerhouse import statement_views as ph_statement
from core.views.powerhouse import client_request_views as ph_request
from core.views.powerhouse import game_views as ph_game
from core.views.powerhouse import kyc_views as ph_kyc
from core.views.powerhouse import support_views as ph_support
from core.views.powerhouse import payment_views as ph_payment
from core.views.powerhouse import settings_views as ph_settings
from core.views.powerhouse import content_views as ph_content
from core.views.powerhouse import bonus_rule_views as ph_bonus_rule
from core.views.powerhouse import bet_views as ph_bet

# Super views
from core.views.super import dashboard_views as su_dashboard
from core.views.super import master_views as su_master
from core.views.super import user_views as su_user
from core.views.super import statement_views as su_statement
from core.views.super import client_request_views as su_request
from core.views.super import kyc_views as su_kyc
from core.views.super import support_views as su_support
from core.views.super import payment_views as su_payment

# Master views
from core.views.master import dashboard_views as ma_dashboard
from core.views.master import user_views as ma_user
from core.views.master import statement_views as ma_statement
from core.views.master import client_request_views as ma_request
from core.views.master import profit_loss_views as ma_profit
from core.views.master import activity_views as ma_activity
from core.views.master import profile_views as ma_profile
from core.views.master import payment_views as ma_payment

# User views
from core.views.user import dashboard_views as us_dashboard
from core.views.user import game_views as us_game
from core.views.user import statement_views as us_statement
from core.views.user import bet_views as us_bet
from core.views.user import profit_loss_views as us_profit
from core.views.user import password_views as us_password
from core.views.user import activity_views as us_activity
from core.views.user import result_views as us_result
from core.views.user import deposit_views as us_deposit
from core.views.user import withdraw_views as us_withdraw
from core.views.user import transaction_views as us_transaction
from core.views.user import profile_views as us_profile
from core.views.user import referral_views as us_referral
from core.views.user import bonus_views as us_bonus
from core.views.user import ticket_views as us_tickets
from core.views.user import settings_views as us_settings
from core.views.user import kyc_views as us_kyc
from core.views import chat_views as chat_views

urlpatterns = [
    # =============================================================================
    # AUTH ROUTES
    # =============================================================================
    path('auth/login', login_view, name='auth-login'),
    path('auth/register', register_view, name='auth-register'),
    path('auth/send-otp', send_otp_view, name='auth-send-otp'),
    path('auth/verify-otp', verify_otp_view, name='auth-verify-otp'),
    path('auth/me', me_view, name='auth-me'),
    path('auth/logout', logout_view, name='auth-logout'),
    path('auth/refresh', refresh_token_view, name='auth-refresh'),
    path('auth/change-password', change_password_view, name='auth-change-password'),
    
    # =============================================================================
    # PUBLIC ROUTES (unauthenticated)
    # =============================================================================
    path('public/games/', pub_views.public_game_list, name='public-games'),
    path('public/games/<int:game_id>/', pub_views.public_game_detail, name='public-game-detail'),
    path('public/providers/', pub_views.public_provider_list, name='public-providers'),
    path('public/categories/', pub_views.public_category_list, name='public-categories'),
    path('public/content/', pub_views.public_content, name='public-content'),
    path('callback/', game_callback_views.game_callback, name='game-callback'),
    
    # =============================================================================
    # POWERHOUSE ROUTES
    # =============================================================================
    # Dashboard
    path('powerhouse/dashboard', ph_dashboard.dashboard_stats, name='powerhouse-dashboard'),
    path('powerhouse/bets/', ph_bet.bet_list, name='powerhouse-bet-list'),
    
    # Super management
    path('powerhouse/supers/', ph_super.super_list_create, name='powerhouse-super-list'),
    path('powerhouse/supers/<int:user_id>/', ph_super.super_detail, name='powerhouse-super-detail'),
    path('powerhouse/supers/<int:user_id>/suspend/', ph_super.super_suspend, name='powerhouse-super-suspend'),
    path('powerhouse/supers/<int:user_id>/activate/', ph_super.super_activate, name='powerhouse-super-activate'),
    
    # Master management
    path('powerhouse/masters/', ph_master.master_list_create, name='powerhouse-master-list'),
    path('powerhouse/masters/<int:user_id>/', ph_master.master_detail, name='powerhouse-master-detail'),
    path('powerhouse/masters/<int:user_id>/suspend/', ph_master.master_suspend, name='powerhouse-master-suspend'),
    path('powerhouse/masters/<int:user_id>/activate/', ph_master.master_activate, name='powerhouse-master-activate'),
    
    # User management
    path('powerhouse/users/', ph_user.user_list_create, name='powerhouse-user-list'),
    path('powerhouse/users/<int:user_id>/', ph_user.user_detail, name='powerhouse-user-detail'),
    path('powerhouse/users/<int:user_id>/suspend/', ph_user.user_suspend, name='powerhouse-user-suspend'),
    path('powerhouse/users/<int:user_id>/activate/', ph_user.user_activate, name='powerhouse-user-activate'),
    path('powerhouse/users/<int:user_id>/adjust-balance/', ph_user.user_adjust_balance, name='powerhouse-user-adjust'),
    
    # Statements
    path('powerhouse/statements/account/', ph_statement.account_statement, name='powerhouse-account-statement'),
    path('powerhouse/statements/bonus/', ph_statement.bonus_statement, name='powerhouse-bonus-statement'),
    path('powerhouse/statements/grant-bonus/', ph_statement.grant_bonus, name='powerhouse-grant-bonus'),
    
    # Client Requests
    path('powerhouse/requests/deposit/', ph_request.deposit_list, name='powerhouse-deposit-list'),
    path('powerhouse/requests/withdraw/', ph_request.withdraw_list, name='powerhouse-withdraw-list'),
    path('powerhouse/requests/total-dw/', ph_request.total_dw, name='powerhouse-total-dw'),
    path('powerhouse/requests/super-master-dw/', ph_request.super_master_dw, name='powerhouse-super-master-dw'),
    path('powerhouse/requests/<int:request_id>/approve/', ph_request.approve_request, name='powerhouse-request-approve'),
    path('powerhouse/requests/<int:request_id>/reject/', ph_request.reject_request, name='powerhouse-request-reject'),
    
    # Game Provider
    path('powerhouse/providers/', ph_game.provider_list_create, name='powerhouse-provider-list'),
    path('powerhouse/providers/<int:provider_id>/', ph_game.provider_detail, name='powerhouse-provider-detail'),
    path('powerhouse/providers/<int:provider_id>/toggle/', ph_game.provider_toggle_status, name='powerhouse-provider-toggle'),
    
    # Game Management
    path('powerhouse/games/', ph_game.game_list_create, name='powerhouse-game-list'),
    path('powerhouse/games/<int:game_id>/', ph_game.game_detail, name='powerhouse-game-detail'),
    path('powerhouse/games/<int:game_id>/toggle/', ph_game.game_toggle_status, name='powerhouse-game-toggle'),
    
    # KYC Management
    path('powerhouse/kyc/', ph_kyc.kyc_list, name='powerhouse-kyc-list'),
    path('powerhouse/kyc/<int:kyc_id>/', ph_kyc.kyc_detail, name='powerhouse-kyc-detail'),
    path('powerhouse/kyc/<int:kyc_id>/approve/', ph_kyc.kyc_approve, name='powerhouse-kyc-approve'),
    path('powerhouse/kyc/<int:kyc_id>/reject/', ph_kyc.kyc_reject, name='powerhouse-kyc-reject'),
    
    # Support Tickets
    path('powerhouse/tickets/', ph_support.ticket_list, name='powerhouse-ticket-list'),
    path('powerhouse/tickets/<int:ticket_id>/', ph_support.ticket_detail, name='powerhouse-ticket-detail'),
    path('powerhouse/tickets/<int:ticket_id>/reply/', ph_support.ticket_reply, name='powerhouse-ticket-reply'),
    path('powerhouse/tickets/<int:ticket_id>/close/', ph_support.ticket_close, name='powerhouse-ticket-close'),
    path('powerhouse/tickets/<int:ticket_id>/assign/', ph_support.ticket_assign, name='powerhouse-ticket-assign'),
    
    # Payment Modes
    path('powerhouse/payment-modes/', ph_payment.payment_mode_list_create, name='powerhouse-payment-list'),
    path('powerhouse/payment-modes/<int:payment_id>/', ph_payment.payment_mode_detail, name='powerhouse-payment-detail'),
    path('powerhouse/payment-modes/<int:payment_id>/toggle/', ph_payment.payment_mode_toggle, name='powerhouse-payment-toggle'),
    
    # Super Settings
    path('powerhouse/settings/', ph_settings.settings_list, name='powerhouse-settings-list'),
    path('powerhouse/settings/<int:user_id>/', ph_settings.settings_detail, name='powerhouse-settings-detail'),
    path('powerhouse/settings/<int:user_id>/create/', ph_settings.settings_create, name='powerhouse-settings-create'),
    
    # Site Content (Powerhouse)
    path('powerhouse/content/', ph_content.content_list, name='powerhouse-content-list'),
    path('powerhouse/content/<str:key>/', ph_content.content_detail, name='powerhouse-content-detail'),
    
    # Bonus Rules (Powerhouse)
    path('powerhouse/bonus-rules/', ph_bonus_rule.bonus_rule_list_create, name='powerhouse-bonus-rule-list'),
    path('powerhouse/bonus-rules/<int:rule_id>/', ph_bonus_rule.bonus_rule_detail, name='powerhouse-bonus-rule-detail'),
    path('powerhouse/bonus-rules/<int:rule_id>/toggle/', ph_bonus_rule.bonus_rule_toggle, name='powerhouse-bonus-rule-toggle'),
    
    # =============================================================================
    # SUPER ROUTES
    # =============================================================================
    # Dashboard
    path('super/dashboard', su_dashboard.dashboard_stats, name='super-dashboard'),
    
    # Master management
    path('super/masters/', su_master.master_list_create, name='super-master-list'),
    path('super/masters/<int:user_id>/', su_master.master_detail, name='super-master-detail'),
    path('super/masters/<int:user_id>/suspend/', su_master.master_suspend, name='super-master-suspend'),
    path('super/masters/<int:user_id>/activate/', su_master.master_activate, name='super-master-activate'),
    
    # User management
    path('super/users/', su_user.user_list_create, name='super-user-list'),
    path('super/users/<int:user_id>/', su_user.user_detail, name='super-user-detail'),
    path('super/users/<int:user_id>/suspend/', su_user.user_suspend, name='super-user-suspend'),
    path('super/users/<int:user_id>/activate/', su_user.user_activate, name='super-user-activate'),
    
    # Statements
    path('super/statements/account/', su_statement.account_statement, name='super-account-statement'),
    path('super/statements/bonus/', su_statement.bonus_statement, name='super-bonus-statement'),
    
    # Client Requests
    path('super/requests/deposit/', su_request.deposit_list, name='super-deposit-list'),
    path('super/requests/withdraw/', su_request.withdraw_list, name='super-withdraw-list'),
    path('super/requests/total-dw/', su_request.total_dw, name='super-total-dw'),
    path('super/requests/master-dw/', su_request.master_dw, name='super-master-dw'),
    path('super/requests/<int:request_id>/approve/', su_request.approve_request, name='super-request-approve'),
    path('super/requests/<int:request_id>/reject/', su_request.reject_request, name='super-request-reject'),
    
    # KYC Management
    path('super/kyc/', su_kyc.kyc_list, name='super-kyc-list'),
    path('super/kyc/<int:kyc_id>/', su_kyc.kyc_detail, name='super-kyc-detail'),
    path('super/kyc/<int:kyc_id>/approve/', su_kyc.kyc_approve, name='super-kyc-approve'),
    path('super/kyc/<int:kyc_id>/reject/', su_kyc.kyc_reject, name='super-kyc-reject'),
    
    # Support Tickets
    path('super/tickets/', su_support.ticket_list, name='super-ticket-list'),
    path('super/tickets/<int:ticket_id>/', su_support.ticket_detail, name='super-ticket-detail'),
    path('super/tickets/<int:ticket_id>/reply/', su_support.ticket_reply, name='super-ticket-reply'),
    path('super/tickets/<int:ticket_id>/close/', su_support.ticket_close, name='super-ticket-close'),
    
    # Payment Modes
    path('super/payment-modes/', su_payment.payment_mode_list_create, name='super-payment-list'),
    path('super/payment-modes/<int:payment_id>/', su_payment.payment_mode_detail, name='super-payment-detail'),
    path('super/payment-modes/<int:payment_id>/toggle/', su_payment.payment_mode_toggle, name='super-payment-toggle'),
    
    # =============================================================================
    # MASTER ROUTES
    # =============================================================================
    # Dashboard
    path('master/dashboard', ma_dashboard.dashboard_stats, name='master-dashboard'),
    
    # User management
    path('master/users/', ma_user.user_list_create, name='master-user-list'),
    path('master/users/<int:user_id>/', ma_user.user_detail, name='master-user-detail'),
    path('master/users/<int:user_id>/suspend/', ma_user.user_suspend, name='master-user-suspend'),
    path('master/users/<int:user_id>/activate/', ma_user.user_activate, name='master-user-activate'),
    
    # Statements
    path('master/statements/account/', ma_statement.account_statement, name='master-account-statement'),
    path('master/statements/bonus/', ma_statement.bonus_statement, name='master-bonus-statement'),
    
    # Client Requests
    path('master/requests/deposit/', ma_request.deposit_list, name='master-deposit-list'),
    path('master/requests/withdraw/', ma_request.withdraw_list, name='master-withdraw-list'),
    path('master/requests/total-dw/', ma_request.total_dw, name='master-total-dw'),
    path('master/requests/<int:request_id>/approve/', ma_request.approve_request, name='master-request-approve'),
    path('master/requests/<int:request_id>/reject/', ma_request.reject_request, name='master-request-reject'),
    
    # Profit Loss
    path('master/profit-loss/sports/', ma_profit.profit_loss_sports, name='master-pl-sports'),
    path('master/profit-loss/client/', ma_profit.profit_loss_client, name='master-pl-client'),
    path('master/profit-loss/winners/', ma_profit.top_winners, name='master-top-winners'),
    
    # Client Activity Log
    path('master/activity/', ma_activity.activity_log_list, name='master-activity-list'),
    path('master/activity/<int:user_id>/', ma_activity.user_activity_log, name='master-user-activity'),
    
    # Profile
    path('master/profile/', ma_profile.profile, name='master-profile'),
    path('master/profile/change-password/', ma_profile.change_password, name='master-change-password'),
    
    # Payment Modes
    path('master/payment-modes/', ma_payment.payment_mode_list_create, name='master-payment-list'),
    path('master/payment-modes/<int:payment_id>/', ma_payment.payment_mode_detail, name='master-payment-detail'),
    path('master/payment-modes/<int:payment_id>/toggle/', ma_payment.payment_mode_toggle, name='master-payment-toggle'),
    
    # =============================================================================
    # USER ROUTES
    # =============================================================================
    # Dashboard
    path('user/dashboard', us_dashboard.dashboard_stats, name='user-dashboard'),
    path('user/games/<int:game_id>/launch/', us_game.launch_game, name='user-launch-game'),
    
    # Account Statement
    path('user/statements/account/', us_statement.account_statement, name='user-account-statement'),
    
    # My Bets
    path('user/bets/', us_bet.my_bets, name='user-bets'),
    path('user/bets/<int:bet_id>/', us_bet.bet_detail, name='user-bet-detail'),
    
    # Profit Loss
    path('user/profit-loss/', us_profit.profit_loss, name='user-profit-loss'),
    
    # Change Password
    path('user/change-password/', us_password.change_password, name='user-change-password'),
    
    # Activity Log
    path('user/activity/', us_activity.activity_log, name='user-activity'),
    
    # Results
    path('user/results/', us_result.results, name='user-results'),
    
    # Deposit
    path('user/deposit/', us_deposit.deposit, name='user-deposit'),
    path('user/deposit/payment-modes/', us_deposit.available_payment_modes, name='user-deposit-payment-modes'),
    
    # Withdraw
    path('user/withdraw/', us_withdraw.withdraw, name='user-withdraw'),
    path('user/withdraw/payment-modes/', us_withdraw.my_payment_modes, name='user-withdraw-payment-modes'),
    path('user/withdraw/payment-modes/<int:payment_id>/', us_withdraw.delete_payment_mode, name='user-delete-payment-mode'),
    
    # Transactions
    path('user/transactions/', us_transaction.transactions, name='user-transactions'),
    
    # Profile, Referral, Bonuses, Tickets
    path('user/profile/', us_profile.profile, name='user-profile'),
    path('user/referral/', us_referral.referral, name='user-referral'),
    path('user/bonuses/', us_bonus.bonus_list, name='user-bonuses'),
    path('user/bonuses/apply/', us_bonus.apply_promo, name='user-bonuses-apply'),
    path('user/bonuses/<int:bonus_id>/claim/', us_bonus.claim_bonus, name='user-bonus-claim'),
    path('user/tickets/', us_tickets.ticket_list_or_create, name='user-tickets-list'),
    path('user/tickets/<int:ticket_id>/', us_tickets.ticket_detail, name='user-ticket-detail'),
    path('user/tickets/<int:ticket_id>/reply/', us_tickets.ticket_reply, name='user-ticket-reply'),
    path('user/settings/', us_settings.user_settings, name='user-settings'),
    path('user/kyc/', us_kyc.submit_kyc, name='user-kyc-submit'),
    # Live chat (any authenticated user)
    path('user/chat/partners/', chat_views.chat_partners, name='chat-partners'),
    path('user/chat/history/', chat_views.chat_history, name='chat-history'),
]
