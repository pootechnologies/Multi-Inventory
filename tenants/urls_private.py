from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import TenantTokenObtainPairView
from . import views
urlpatterns = [
    # path('tenants/', views.TenantListCreateView.as_view(), name='tenant-list'),
    # # path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant-detail'),
    # path('users/', views.userListCreateView.as_view(), name='user-list'),
    # # bootstrap public tenant
    # path('bootstrap-public/', views.PublicTenantBootstrapView.as_view(), name='bootstrap-public'),
    # # provision a private tenant
    # path('provision-tenant/', views.ProvisionTenantView.as_view(), name='provision-tenant'),
    # # create tenant users (only tenant owner or tenant admin)
    path('tenant-users/', views.TenantUserCreateView.as_view(), name='tenant-user-create'),
    path('tenant-users/<int:pk>/', views.TenantUserUpdateView.as_view(), name='tenant-user-update'),
    path('tenant/groups/', views.TenantGroupCreateView.as_view(), name='tenant-group-create'),
    path('tenant/groups/<int:pk>/', views.TenantGroupDetailView.as_view(), name='tenant-group-detail'),
    path('users/permissions/', views.UserPermissionsView.as_view(), name='user-permissions'),
    # list all available permissions
    path('tenant/permissions/', views.AvailablePermissionsView.as_view(), name='available-permissions'),
    path('tenant/permissions/current/', views.CurrentTenantPermissionsView.as_view(), name='current-tenant-permissions'),
    path('tenant/permission-protected/', views.TenantPermissionProtectedView.as_view(), name='tenant-permission-protected'),
    
]
urlpatterns += [
    path('token/', TenantTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('init-payment/', views.InitPaymentView.as_view(), name='init-payment'),
    path('payments-verify/', views.PaymentVerifyView.as_view(), name='tenant-payment-list'),
    # chapa payment paths
    path('chapa-initiate/', views.ChapaPaymentInitView.as_view(), name='chapa-initiate-payment'),
    path('chapa-verify/<str:reference>/', views.ChapaPaymentVerifyView.as_view(), name='chapa-verify-payment'),
    # notification path
    # path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
]