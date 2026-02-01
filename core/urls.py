from django.urls import path
from . import views

urlpatterns = [
    # =============================================================================
    # AUTH
    # =============================================================================
    path('auth/login/', views.AuthLoginView.as_view()),
    path('auth/login', views.AuthLoginView.as_view()),
    path('auth/logout/', views.AuthLogoutView.as_view()),
    path('auth/logout', views.AuthLogoutView.as_view()),
    path('auth/me/', views.AuthMeView.as_view()),
    path('auth/me', views.AuthMeView.as_view()),
    path('auth/register/', views.AuthRegisterView.as_view()),
    path('auth/register', views.AuthRegisterView.as_view()),

    # =============================================================================
    # USERS
    # =============================================================================
    path('users/', views.UserListCreateView.as_view()),
    path('users', views.UserListCreateView.as_view()),
    path('users/<int:pk>/', views.UserDetailView.as_view()),
    path('users/<int:pk>', views.UserDetailView.as_view()),
    path('users/<int:pk>/suspend/', views.UserSuspendView.as_view()),
    path('users/<int:pk>/suspend', views.UserSuspendView.as_view()),
    path('users/<int:pk>/change-role/', views.UserChangeRoleView.as_view()),
    path('users/<int:pk>/change-role', views.UserChangeRoleView.as_view()),

    # =============================================================================
    # WALLETS
    # =============================================================================
    path('wallets/my-balance/', views.WalletBalanceView.as_view()),
    path('wallets/my-balance', views.WalletBalanceView.as_view()),
    path('wallets/<int:pk>/', views.WalletUserBalanceView.as_view()),
    path('wallets/<int:pk>', views.WalletUserBalanceView.as_view()),

    # =============================================================================
    # COINS
    # =============================================================================
    path('coins/mint/', views.CoinMintView.as_view()),
    path('coins/mint', views.CoinMintView.as_view()),
    path('coins/transfer/', views.CoinTransferView.as_view()),
    path('coins/transfer', views.CoinTransferView.as_view()),
    path('coins/transactions/', views.CoinTransactionListView.as_view()),
    path('coins/transactions', views.CoinTransactionListView.as_view()),
    path('coins/transactions/export/', views.ExportTransactionsView.as_view()),
    path('coins/transactions/export', views.ExportTransactionsView.as_view()),

    # =============================================================================
    # TRANSACTIONS - DEPOSITS
    # =============================================================================
    path('transactions/deposits/', views.DepositListCreateView.as_view()),
    path('transactions/deposits', views.DepositListCreateView.as_view()),
    path('transactions/deposits/<int:pk>/approve/', views.DepositApproveView.as_view()),
    path('transactions/deposits/<int:pk>/approve', views.DepositApproveView.as_view()),
    path('transactions/deposits/<int:pk>/reject/', views.DepositRejectView.as_view()),
    path('transactions/deposits/<int:pk>/reject', views.DepositRejectView.as_view()),

    # =============================================================================
    # TRANSACTIONS - WITHDRAWALS
    # =============================================================================
    path('transactions/withdrawals/', views.WithdrawalListCreateView.as_view()),
    path('transactions/withdrawals', views.WithdrawalListCreateView.as_view()),
    path('transactions/withdrawals/<int:pk>/approve/', views.WithdrawalApproveView.as_view()),
    path('transactions/withdrawals/<int:pk>/approve', views.WithdrawalApproveView.as_view()),
    path('transactions/withdrawals/<int:pk>/reject/', views.WithdrawalRejectView.as_view()),
    path('transactions/withdrawals/<int:pk>/reject', views.WithdrawalRejectView.as_view()),

    # =============================================================================
    # BETS
    # =============================================================================
    path('bets/', views.BetListCreateView.as_view()),
    path('bets', views.BetListCreateView.as_view()),
    path('bets/export/', views.ExportBetsView.as_view()),
    path('bets/export', views.ExportBetsView.as_view()),
    path('bets/<int:pk>/settle/', views.BetSettleView.as_view()),
    path('bets/<int:pk>/settle', views.BetSettleView.as_view()),
    path('bets/<int:pk>/cancel/', views.BetCancelView.as_view()),
    path('bets/<int:pk>/cancel', views.BetCancelView.as_view()),

    # =============================================================================
    # GAMES
    # =============================================================================
    path('games/categories/', views.CategoryListView.as_view()),
    path('games/categories', views.CategoryListView.as_view()),
    path('games/admin/categories/', views.CategoryAdminView.as_view()),
    path('games/admin/categories', views.CategoryAdminView.as_view()),
    path('games/admin/categories/<int:pk>/', views.CategoryAdminView.as_view()),
    path('games/admin/categories/<int:pk>', views.CategoryAdminView.as_view()),
    path('games/providers/', views.ProviderListView.as_view()),
    path('games/providers', views.ProviderListView.as_view()),
    path('games/admin/all/', views.AdminGameListView.as_view()),
    path('games/admin/all', views.AdminGameListView.as_view()),
    path('games/admin/games/', views.AdminGameCreateUpdateView.as_view()),
    path('games/admin/games', views.AdminGameCreateUpdateView.as_view()),
    path('games/admin/games/<int:pk>/', views.AdminGameCreateUpdateView.as_view()),
    path('games/admin/games/<int:pk>', views.AdminGameCreateUpdateView.as_view()),
    path('games/admin/providers/', views.ProviderAdminView.as_view()),
    path('games/admin/providers', views.ProviderAdminView.as_view()),
    path('games/admin/providers/<int:pk>/', views.ProviderAdminView.as_view()),
    path('games/admin/providers/<int:pk>', views.ProviderAdminView.as_view()),
    path('games/<int:pk>/launch/', views.GameLaunchView.as_view()),
    path('games/<int:pk>/launch', views.GameLaunchView.as_view()),
    path('games/<slug:slug>/launch/', views.GameLaunchView.as_view()),
    path('games/<slug:slug>/launch', views.GameLaunchView.as_view()),
    path('games/<int:pk>/', views.GameDetailView.as_view()),
    path('games/<int:pk>', views.GameDetailView.as_view()),
    path('games/<slug:slug>/', views.GameDetailView.as_view()),
    path('games/<slug:slug>', views.GameDetailView.as_view()),
    path('games/', views.GameListView.as_view()),
    path('games', views.GameListView.as_view()),

    # =============================================================================
    # KYC
    # =============================================================================
    path('kyc/upload/', views.KYCUploadView.as_view()),
    path('kyc/upload', views.KYCUploadView.as_view()),
    path('kyc/status/', views.KYCStatusView.as_view()),
    path('kyc/status', views.KYCStatusView.as_view()),
    path('kyc/pending/', views.KYCPendingView.as_view()),
    path('kyc/pending', views.KYCPendingView.as_view()),
    path('kyc/<int:pk>/approve/', views.KYCApproveRejectView.as_view(), {'action': 'approve'}),
    path('kyc/<int:pk>/approve', views.KYCApproveRejectView.as_view(), {'action': 'approve'}),
    path('kyc/<int:pk>/reject/', views.KYCApproveRejectView.as_view(), {'action': 'reject'}),
    path('kyc/<int:pk>/reject', views.KYCApproveRejectView.as_view(), {'action': 'reject'}),

    # =============================================================================
    # SUPPORT / TICKETS
    # =============================================================================
    path('support/tickets/', views.TicketListCreateView.as_view()),
    path('support/tickets', views.TicketListCreateView.as_view()),
    path('support/tickets/<int:pk>/reply/', views.TicketReplyView.as_view()),
    path('support/tickets/<int:pk>/reply', views.TicketReplyView.as_view()),
    path('support/tickets/<int:pk>/close/', views.TicketCloseView.as_view()),
    path('support/tickets/<int:pk>/close', views.TicketCloseView.as_view()),

    # =============================================================================
    # ADMIN DASHBOARD
    # =============================================================================
    path('dashboard/admin-stats/', views.AdminDashboardStatsView.as_view()),
    path('dashboard/admin-stats', views.AdminDashboardStatsView.as_view()),

    # =============================================================================
    # CONFIG - SYSTEM
    # =============================================================================
    path('config/system/', views.SystemConfigView.as_view()),
    path('config/system', views.SystemConfigView.as_view()),

    # =============================================================================
    # CONFIG - BANNERS
    # =============================================================================
    path('config/banners/', views.PromoBannerListView.as_view()),
    path('config/banners', views.PromoBannerListView.as_view()),

    # =============================================================================
    # CONFIG - PAYMENT METHODS
    # =============================================================================
    path('config/payment-methods/', views.PaymentMethodListCreateView.as_view()),
    path('config/payment-methods', views.PaymentMethodListCreateView.as_view()),
    path('config/payment-methods/<int:pk>/', views.PaymentMethodUpdateView.as_view()),
    path('config/payment-methods/<int:pk>', views.PaymentMethodUpdateView.as_view()),

    # =============================================================================
    # CONFIG - BONUS RULES
    # =============================================================================
    path('config/bonus-rules/', views.BonusRuleListCreateView.as_view()),
    path('config/bonus-rules', views.BonusRuleListCreateView.as_view()),

    # =============================================================================
    # CONFIG - LIMITS
    # =============================================================================
    path('config/limits/', views.LimitListCreateView.as_view()),
    path('config/limits', views.LimitListCreateView.as_view()),

    # =============================================================================
    # USER STATS (for user dashboard)
    # =============================================================================
    path('users/me/stats/', views.UserStatsView.as_view()),
    path('users/me/stats', views.UserStatsView.as_view()),

    # =============================================================================
    # USER BONUSES
    # =============================================================================
    path('bonuses/my/', views.UserBonusesView.as_view()),
    path('bonuses/my', views.UserBonusesView.as_view()),
    path('bonuses/<int:pk>/claim/', views.ClaimBonusView.as_view()),
    path('bonuses/<int:pk>/claim', views.ClaimBonusView.as_view()),
    path('bonuses/redeem-promo/', views.RedeemPromoCodeView.as_view()),
    path('bonuses/redeem-promo', views.RedeemPromoCodeView.as_view()),

    # =============================================================================
    # PROMO CODES
    # =============================================================================
    path('promo-codes/', views.PromoCodeListView.as_view()),
    path('promo-codes', views.PromoCodeListView.as_view()),

    # =============================================================================
    # USER REFERRALS
    # =============================================================================
    path('referrals/my/', views.UserReferralsView.as_view()),
    path('referrals/my', views.UserReferralsView.as_view()),

    # =============================================================================
    # FAVORITES
    # =============================================================================
    path('favorites/', views.FavoritesView.as_view()),
    path('favorites', views.FavoritesView.as_view()),
    path('favorites/<str:game_id>/', views.FavoriteDeleteView.as_view()),
    path('favorites/<str:game_id>', views.FavoriteDeleteView.as_view()),

    # =============================================================================
    # USER SETTINGS
    # =============================================================================
    path('users/me/settings/', views.UserSettingsView.as_view()),
    path('users/me/settings', views.UserSettingsView.as_view()),

    # =============================================================================
    # USER PASSWORD CHANGE
    # =============================================================================
    path('users/me/password/', views.UserPasswordChangeView.as_view()),
    path('users/me/password', views.UserPasswordChangeView.as_view()),

    # =============================================================================
    # PUBLIC APIs (No Auth Required)
    # =============================================================================
    path('public/testimonials/', views.TestimonialListView.as_view()),
    path('public/testimonials', views.TestimonialListView.as_view()),
    path('public/live-wins/', views.LiveWinsView.as_view()),
    path('public/live-wins', views.LiveWinsView.as_view()),
    path('public/stats/', views.PlatformStatsView.as_view()),
    path('public/stats', views.PlatformStatsView.as_view()),

    # =============================================================================
    # REFERRAL TIERS
    # =============================================================================
    path('config/referral-tiers/', views.ReferralTierListView.as_view()),
    path('config/referral-tiers', views.ReferralTierListView.as_view()),

    # =============================================================================
    # POWERHOUSE APIs (Root Level - Platform Owner)
    # =============================================================================
    path('powerhouse/stats/', views.PowerHouseDashboardStatsView.as_view()),
    path('powerhouse/stats', views.PowerHouseDashboardStatsView.as_view()),
    path('powerhouse/superadmins/', views.PowerHouseSuperAdminListView.as_view()),
    path('powerhouse/superadmins', views.PowerHouseSuperAdminListView.as_view()),
    path('powerhouse/superadmins/create/', views.PowerHouseCreateSuperAdminView.as_view()),
    path('powerhouse/superadmins/create', views.PowerHouseCreateSuperAdminView.as_view()),
    path('powerhouse/mint/', views.PowerHouseMintCoinsView.as_view()),
    path('powerhouse/mint', views.PowerHouseMintCoinsView.as_view()),
    path('powerhouse/emergency-suspend/', views.PowerHouseEmergencySuspendView.as_view()),
    path('powerhouse/emergency-suspend', views.PowerHouseEmergencySuspendView.as_view()),
    path('powerhouse/audit-logs/', views.PowerHouseAuditLogsView.as_view()),
    path('powerhouse/audit-logs', views.PowerHouseAuditLogsView.as_view()),
    path('powerhouse/global-wallets/', views.PowerHouseGlobalWalletsView.as_view()),
    path('powerhouse/global-wallets', views.PowerHouseGlobalWalletsView.as_view()),
    path('powerhouse/users/<int:pk>/suspend/', views.PowerHouseSuspendUserView.as_view()),
    path('powerhouse/users/<int:pk>/suspend', views.PowerHouseSuspendUserView.as_view()),

    # =============================================================================
    # SUPERADMIN APIs (Platform Management)
    # =============================================================================
    path('superadmin/stats/', views.SuperAdminDashboardStatsView.as_view()),
    path('superadmin/stats', views.SuperAdminDashboardStatsView.as_view()),
    path('superadmin/masters/', views.SuperAdminMasterListView.as_view()),
    path('superadmin/masters', views.SuperAdminMasterListView.as_view()),
    path('superadmin/masters/create/', views.SuperAdminCreateMasterView.as_view()),
    path('superadmin/masters/create', views.SuperAdminCreateMasterView.as_view()),
    path('superadmin/masters/<int:pk>/limits/', views.SuperAdminSetMasterLimitsView.as_view()),
    path('superadmin/masters/<int:pk>/limits', views.SuperAdminSetMasterLimitsView.as_view()),
    path('superadmin/masters/<int:pk>/suspend/', views.SuperAdminSuspendMasterView.as_view()),
    path('superadmin/masters/<int:pk>/suspend', views.SuperAdminSuspendMasterView.as_view()),
    path('superadmin/transfer/', views.SuperAdminTransferCoinsView.as_view()),
    path('superadmin/transfer', views.SuperAdminTransferCoinsView.as_view()),
    path('superadmin/reports/', views.SuperAdminReportsView.as_view()),
    path('superadmin/reports', views.SuperAdminReportsView.as_view()),

    # =============================================================================
    # MASTER APIs (Agent/Operator)
    # =============================================================================
    path('master/stats/', views.MasterDashboardStatsView.as_view()),
    path('master/stats', views.MasterDashboardStatsView.as_view()),
    path('master/users/', views.MasterUserListView.as_view()),
    path('master/users', views.MasterUserListView.as_view()),
    path('master/users/create/', views.MasterCreateUserView.as_view()),
    path('master/users/create', views.MasterCreateUserView.as_view()),
    path('master/users/<int:pk>/suspend/', views.MasterSuspendUserView.as_view()),
    path('master/users/<int:pk>/suspend', views.MasterSuspendUserView.as_view()),
    path('master/users/<int:pk>/password/', views.MasterResetUserPasswordView.as_view()),
    path('master/users/<int:pk>/password', views.MasterResetUserPasswordView.as_view()),
    path('master/users/<int:pk>/betting-limit/', views.MasterSetUserBettingLimitView.as_view()),
    path('master/users/<int:pk>/betting-limit', views.MasterSetUserBettingLimitView.as_view()),
    path('master/users/<int:pk>/deposit/', views.MasterDepositForUserView.as_view()),
    path('master/users/<int:pk>/deposit', views.MasterDepositForUserView.as_view()),
    path('master/users/<int:pk>/withdraw/', views.MasterWithdrawForUserView.as_view()),
    path('master/users/<int:pk>/withdraw', views.MasterWithdrawForUserView.as_view()),
    path('master/users/<int:pk>/bets/', views.MasterUserBetHistoryView.as_view()),
    path('master/users/<int:pk>/bets', views.MasterUserBetHistoryView.as_view()),
]
