# client/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),
    path('users/<int:id>/', views.PublicProfileView.as_view(), name='public-profile'),
    
    # Follow
    path('users/<int:user_id>/follow/', views.FollowView.as_view(), name='follow'),
    path('users/<int:user_id>/followers/', views.FollowersView.as_view(), name='followers'),
    path('users/<int:user_id>/following/', views.FollowingView.as_view(), name='following'),
    
    # Feed
    path('feed/', views.FeedView.as_view(), name='feed'),
    
    # Posts (Productos)
    path('posts/', views.PostListCreateView.as_view(), name='posts'),
    path('posts/my/', views.MyPostsView.as_view(), name='my-posts'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/like/', views.PostLikeView.as_view(), name='post-like'),
    path('sellers/<int:seller_id>/posts/', views.SellerPostsView.as_view(), name='seller-posts'),
    
    # Messages
    path('messages/', views.MessageListCreateView.as_view(), name='messages'),
    path('messages/my/', views.MyMessagesView.as_view(), name='my-messages'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:message_id>/like/', views.MessageLikeView.as_view(), name='message-like'),
    path('sellers/<int:seller_id>/messages/', views.SellerMessagesView.as_view(), name='seller-messages'),
    
    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', views.NotificationDeleteView.as_view(), name='notification-delete'),
    path('notifications/<int:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark-read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark-all-read'),
    path('notifications/delete-all/', views.DeleteAllNotificationsView.as_view(), name='delete-all'),
    
    # Explorar
    path('explore/content/', views.ExploreContentView.as_view(), name='explore-content'),
    path('explore/sellers/', views.ExploreSellersView.as_view(), name='explore-sellers'),
    
    
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:user_id>/activity/', views.AdminUserActivityView.as_view(), name='admin-user-activity'),
    path('admin/users/<int:user_id>/toggle-staff/', views.AdminUserToggleStaffView.as_view(), name='admin-toggle-staff'),
    path('admin/users/<int:user_id>/toggle-active/', views.AdminUserToggleActiveView.as_view(), name='admin-toggle-active'),
    path('admin/users/<int:id>/delete/', views.AdminUserDeleteView.as_view(), name='admin-user-delete'),
    path('admin/posts/', views.AdminPostListView.as_view(), name='admin-posts'),
    path('admin/posts/<int:id>/', views.AdminPostDeleteView.as_view(), name='admin-post-delete'),
    path('admin/messages/', views.AdminMessageListView.as_view(), name='admin-messages'),
    path('admin/messages/<int:id>/', views.AdminMessageDeleteView.as_view(), name='admin-message-delete'),
    path('admin/users/<int:user_id>/toggle-active/', views.AdminUserToggleActiveView.as_view(), name='admin-toggle-active'),
    path('admin/users/<int:user_id>/toggle-store/', views.AdminUserToggleStoreView.as_view(), name='admin-toggle-store'),
    path('admin/users/<int:user_id>/resend-verification/', views.AdminUserResendVerificationView.as_view(), name='admin-resend-verification'),
    path('admin/users/<int:user_id>/verify-email/', views.AdminUserVerifyEmailView.as_view(), name='admin-verify-email'),
    
    path('reports/', views.ReportCreateView.as_view(), name='report-create'),
    
    # Admin reportes
    path('admin/reports/', views.AdminReportListView.as_view(), name='admin-reports'),
    path('admin/reports/<int:report_id>/dismiss/', views.AdminReportDismissView.as_view(), name='admin-report-dismiss'),
    path('admin/reports/<int:report_id>/resolve/', views.AdminReportResolveView.as_view(), name='admin-report-resolve'),


    # Soporte - Usuarios
    path('support/tickets/', views.UserTicketListView.as_view(), name='user-tickets'),
    path('support/tickets/create/', views.UserTicketCreateView.as_view(), name='create-ticket'),
    path('support/tickets/<int:pk>/', views.UserTicketDetailView.as_view(), name='ticket-detail'),
    path('support/tickets/<int:ticket_id>/messages/', views.UserTicketMessageCreateView.as_view(), name='ticket-message'),
    
    # Soporte - Admin (gestión)
    path('admin/support/tickets/', views.AdminTicketListView.as_view(), name='admin-tickets'),
    path('admin/support/tickets/<int:id>/', views.AdminTicketDetailView.as_view(), name='admin-ticket-detail'),
    path('admin/support/tickets/<int:ticket_id>/assign/', views.AdminTicketAssignView.as_view(), name='ticket-assign'),
    path('admin/support/tickets/<int:ticket_id>/status/', views.AdminTicketStatusView.as_view(), name='ticket-status'),
    path('admin/support/tickets/<int:id>/delete/', views.AdminTicketDeleteView.as_view(), name='admin-ticket-delete'),
    path('admin/support/tickets/<int:ticket_id>/reply/', views.AdminTicketReplyView.as_view(), name='ticket-reply'),
    
    # FAQ - Públicas
    path('faq/', views.FAQListView.as_view(), name='faq-list'),
    
    # FAQ - Admin
    path('admin/faq/', views.AdminFAQListView.as_view(), name='admin-faq-list'),
    path('admin/faq/create/', views.AdminFAQCreateView.as_view(), name='faq-create'),
    path('admin/faq/<int:id>/', views.AdminFAQUpdateView.as_view(), name='faq-update'),
    
    
    # Verificación de email
    path('auth/verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend-verification'),
    
    # Recuperación de contraseña
    path('auth/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset/validate/', views.PasswordResetValidateView.as_view(), name='password-reset-validate'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]