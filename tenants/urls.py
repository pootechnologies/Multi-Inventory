from django.urls import path
from . import views

from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import TenantTokenObtainPairView


urlpatterns = [
    # path('tenants/', views.TenantListCreateView.as_view(), name='tenant-list'),
    # path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant-detail'),
    # path('users/', views.userListCreateView.as_view(), name='user-list'),
    # bootstrap public tenant
    path('bootstrap-public/', views.PublicTenantBootstrapView.as_view(), name='bootstrap-public'),
    # provision a private tenant
    path('provision-tenant/', views.ProvisionTenantView.as_view(), name='provision-tenant'),
    path('email/verify/', views.EmailVerificationView.as_view(), name='email-verify'),
    path('email/resend/', views.EmailVerificationResendView.as_view(), name='email-verification-resend'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password/reset-password/', views.PasswordResetConfirmView.as_view(), name='password-reset-page'),
    # business_categotry
    path('business-categories/', views.BusinessCategoryListCreateView.as_view(), name='business-category-list'),
    path('business-categories/<int:pk>/', views.BusinessCategoryDetailView.as_view(), name='business-category-detail'),
    # create tenant users (only tenant owner or tenant admin)
    # path('tenant-users/', views.TenantUserCreateView.as_view(), name='tenant-user-create'),
    # create tenant-scoped groups
    path('tenant/groups/', views.TenantGroupCreateView.as_view(), name='tenant-group-create'),
    path('tenant/groups/<int:pk>/', views.TenantGroupDetailView.as_view(), name='tenant-group-detail'),
    # # list all available permissions
    path('tenant/permissions/', views.AvailablePermissionsView.as_view(), name='available-permissions'),
    path('tenant/permissions/current/', views.CurrentTenantPermissionsView.as_view(), name='current-tenant-permissions'),
    path('tenant/permission-protected/', views.TenantPermissionProtectedView.as_view(), name='tenant-permission-protected'),
    path('init-paymentlist/', views.InitPaymentListView.as_view(), name='tenant-payment-list'),
    path('update-payments/<int:pk>/', views.InitPaymentDetailView.as_view(), name='tenant-payment-update'),
    path('Subscription-plans/', views.SubscriptionPlanListCreateView.as_view(), name='subscription-plan-list'),
    path('Subscription-plans/<int:pk>/', views.SubscriptionPlanDetailView.as_view(), name='subscription-plan-detail'),
    # Chapa webhook endpoint for payment callbacks
    path('payments/chapa/webhook/', views.chapa_webhook, name='chapa-webhook'),
]

urlpatterns += [
    path('token/', TenantTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
