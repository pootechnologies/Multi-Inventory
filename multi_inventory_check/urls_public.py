from django.contrib import admin
from django.urls import path, include
# Public (shared) URL configuration. These routes are served from the public schema
# and typically include tenant management endpoints like creating a new tenant.

urlpatterns = [
    path('tenants/', include('tenants.urls')),  
    path('admin/', admin.site.urls),
    # path('api/', include('inventory.urls')),
]