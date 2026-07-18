#  tenants/admin.py

from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from tenants.models import Tenant, Domain, UserAccount


class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = [
        "name", 
        "schema_name", 
        "paid_until", 
        "on_trial"
        ]


class DomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "tenant", "is_primary"]


class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "is_active", "last_login", "date_joined", "is_staff", "is_superuser"]
    list_display_links = ["id", "email"]
    search_fields = ["email"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "email",
                    "password",
                ],
            },
        ),
        (
            "Administrative",
            {
                "fields": [
                    # "tenants",
                    "last_login",
                    "is_active",
                    # "is_verified",
                ],
            },
        ),
    ]


admin.site.register(Tenant, TenantAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(UserAccount)
