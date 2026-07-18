from rest_framework import permissions, serializers
from django_tenants.utils import get_public_schema_name, schema_context
from django.contrib.auth.models import Group, Permission
from .models import UserAccount
import logging
class IsTenantOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        tenant = getattr(request, 'tenant', None)
        if not tenant or not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user == tenant.owner or getattr(request.user, 'usertenantpermissions', None) and request.user.usertenantpermissions.is_superuser
        except Exception:
            return False
class IsTenantUser(permissions.BasePermission):
    def has_permission(self, request, view):
        logger = logging.getLogger(__name__)
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        is_auth = bool(user and getattr(user, 'is_authenticated', False))
        allowed = False
        if not tenant or not user or not is_auth:
            allowed = False
        else:
            try:
                allowed = tenant in user.tenants.all()
            except Exception:
                allowed = False

        # Debug info to help diagnose permission issues during testing
        logger.debug(
            "IsTenantUser.has_permission -> user=%s is_authenticated=%s tenant=%s allowed=%s",
            getattr(user, 'email', repr(user)), is_auth, getattr(tenant, 'id', tenant), allowed,
        )

        return allowed

class HasModelPermissionForTenant(permissions.BasePermission):
    """
    Tenant-aware model permission class.
    Maps view.action or HTTP method to model permissions:
      list/retrieve/GET -> view_{model}
      create/POST -> add_{model}
      update/partial_update/PUT/PATCH -> change_{model}
      destroy/DELETE -> delete_{model}
    Checks permissions inside tenant schema.
    """
    action_map = {
        'create': 'add',
        'update': 'change',
        'partial_update': 'change',
        'destroy': 'delete',
        'retrieve': 'view',
        'list': 'view',
    }
    
    method_to_action_map = {
        'GET': 'list',
        'POST': 'create',
        'PUT': 'update',
        'PATCH': 'partial_update',
        'DELETE': 'destroy',
    }

    def has_permission(self, request, view):
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        if not tenant or not user or not getattr(user, 'is_authenticated', False):
            return False

        # Check explicit permission_required on view
        perm = getattr(view, 'permission_required', None)
        
        # If no explicit perm, try to infer from action + model
        if not perm:
            action = getattr(view, 'action', None)
            
            # For APIView (no action), map HTTP method to action
            if not action:
                action = self.method_to_action_map.get(request.method, None)
            
            if action:
                codename_prefix = self.action_map.get(action, None)
                # Get model from view.queryset
                queryset = getattr(view, 'queryset', None)
                model = getattr(queryset, 'model', None) if hasattr(queryset, 'model') else None
                if codename_prefix and model:
                    perm = f"{model._meta.app_label}.{codename_prefix}_{model._meta.model_name}"
        
        if not perm:
            # No permission to check; deny by default for security
            return False

        try:
            with schema_context(tenant.schema_name):
                tenant_user = UserAccount.objects.get(pk=user.pk)
                return tenant_user.has_perm(perm)
        except Exception:
            return False

class HasTenantPermission(permissions.BasePermission):
    permission_required = None

    def has_permission(self, request, view):
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        if not tenant or not user or not getattr(user, 'is_authenticated', False):
            return False

        perm = getattr(view, 'permission_required', None)
        if not perm:
            return False

        try:
            with schema_context(tenant.schema_name):
                tenant_user = UserAccount.objects.get(pk=user.pk)
                return tenant_user.has_perm(perm)
        except Exception:
            return False