from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate
from django_tenants.utils import schema_context, get_public_schema_name
from .models import UserAccount, Tenant


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        request = self.context.get('request')

        # Authenticate user (backend may accept email or username)
        # Prefer validated attrs, but fall back to raw request.data to accept keys like 'email'
        identifier = (
            attrs.get(self.username_field)
            or attrs.get('username')
            or attrs.get('email')
            or (request.data.get('email') if request is not None else None)
            or (request.data.get('username') if request is not None else None)
        )
        user = None
        # password may be in attrs or raw data depending on serializer field names
        password = attrs.get('password') or (request.data.get('password') if request is not None else None)
        if identifier and password:
            user = authenticate(request=request, username=identifier, password=password)

        # Fallback: if the auth backend couldn't authenticate (often due to tenant schema
        # context differences), try to find the user in the public schema and verify password
        # directly. This lets tenant users authenticate from the central endpoint by email.
        if not user:
            public_name = get_public_schema_name()
            with schema_context(public_name):
                u = None
                if identifier:
                    u = UserAccount.objects.filter(email__iexact=identifier).first() 
                    # or UserAccount.objects.filter(username__iexact=identifier).first()
                if u and password and u.check_password(password):
                    user = u

        if not user:
            raise AuthenticationFailed('Invalid credentials')

        # Determine tenant context and enforce membership if logging in inside a specific tenant
        tenant = getattr(request, 'tenant', None)
        public_name = get_public_schema_name()

        # If login is inside a tenant that is not the public schema, ensure user is a member
        if tenant and tenant.schema_name != public_name:
            with schema_context(public_name):
                if not UserAccount.objects.filter(pk=user.pk, tenants=tenant).exists():
                    raise AuthenticationFailed('User is not a member of this tenant')

        # Proceed with standard token creation
        data = super().validate(attrs)
        data['user'] = {'id': user.id, 'email': user.email, 'tenant': tenant.schema_name if tenant else None}
        data['tenant_groups'] = []
        data['tenant_permissions'] = []

        def attach_tenant_permissions(schema_name):
            with schema_context(schema_name):
                try:
                    # Refetch user inside tenant schema to ensure proper permissions access
                    tenant_user = UserAccount.objects.get(pk=user.pk)
                    data['tenant_groups'] = [g.name for g in tenant_user.usertenantpermissions.groups.all()]
                except Exception as e:
                    data['tenant_groups'] = []
                try:
                    # Get all permissions (including group-derived permissions) inside tenant schema
                    tenant_user = UserAccount.objects.get(pk=user.pk)
                    data['tenant_permissions'] = sorted(tenant_user.get_all_permissions())
                except Exception as e:
                    data['tenant_permissions'] = []

        # If no tenant context or the context is the public schema, return the list of tenant
        # memberships for this user (central login). Otherwise, include the specific tenant.
        # Also accept an explicit `tenant_schema` in the login payload to request a token
        # for a specific tenant when authenticating from the central/public endpoint.
        requested_schema = None
        if request is not None:
            requested_schema = request.data.get('tenant_schema') or request.data.get('tenant') or request.data.get('tenant_id')

        if requested_schema:
            with schema_context(public_name):
                requested_tenant = Tenant.objects.filter(schema_name=requested_schema).first()
                if not requested_tenant:
                    raise AuthenticationFailed('Requested tenant not found')
                # Ensure membership
                if not UserAccount.objects.filter(pk=user.pk, tenants=requested_tenant).exists():
                    raise AuthenticationFailed('User is not a member of the requested tenant')
                attach_tenant_permissions(requested_tenant.schema_name)
                data['tenant'] = {'id': requested_tenant.id, 'schema_name': requested_tenant.schema_name}
                return data

        if not tenant or tenant.schema_name == public_name:
            with schema_context(public_name):
                memberships = []
                # Exclude the public schema from the membership list
                qs = user.tenants.exclude(schema_name=public_name).all()
                for t in qs:
                    memberships.append({'id': t.id, 'schema_name': t.schema_name, 'name': getattr(t, 'name', None)})
                data['tenants'] = memberships

            # If logging in from public schema, auto-load permissions for the first tenant membership
            if memberships:
                attach_tenant_permissions(memberships[0]['schema_name'])
        else:
            attach_tenant_permissions(tenant.schema_name)
            data['tenant'] = {'id': tenant.id, 'schema_name': tenant.schema_name}

        return data


class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer


# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import authenticate
# from django_tenants.utils import schema_context, get_public_schema_name
# from .models import UserAccount


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         # authenticate using Django backends (accepts username or email depending on backend)
#         user = authenticate(request=self.context.get('request'), username=attrs.get(self.username_field), password=attrs.get('password'))
#         if not user:
#             raise AuthenticationFailed('Invalid credentials')

#         # If request is within a tenant, ensure the user is a member of that tenant.
#         tenant = getattr(self.context.get('request'), 'tenant', None)
#         if tenant:
#             # Users and their tenant relation are stored in public schema; check there.
#             with schema_context(get_public_schema_name()):
#                 if not UserAccount.objects.filter(pk=user.pk, tenants=tenant).exists():
#                     raise AuthenticationFailed('User is not a member of this tenant')

#         # proceed to generate tokens
#         data = super().validate(attrs)
#         data['user'] = {'id': user.id, 'email': user.email, 'tenant': tenant.schema_name if tenant else None}

#         return data

# class TenantTokenObtainPairView(TokenObtainPairView):
#     serializer_class = TenantTokenObtainPairSerializer


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         request = self.context.get('request')

#         # Authenticate user (backend may accept email or username)
#         # Prefer validated attrs, but fall back to raw request.data to accept keys like 'email'
#         identifier = (
#             attrs.get(self.username_field)
#             or attrs.get('username')
#             or attrs.get('email')
#             or (request.data.get('email') if request is not None else None)
#             or (request.data.get('username') if request is not None else None)
#         )
#         user = None
#         # password may be in attrs or raw data depending on serializer field names
#         password = attrs.get('password') or (request.data.get('password') if request is not None else None)
#         if identifier and password:
#             user = authenticate(request=request, username=identifier, password=password)

#         # Fallback: if the auth backend couldn't authenticate (often due to tenant schema
#         # context differences), try to find the user in the public schema and verify password
#         # directly. This lets tenant users authenticate from the central endpoint by email.
#         if not user:
#             public_name = get_public_schema_name()
#             with schema_context(public_name):
#                 u = None
#                 if identifier:
#                     u = UserAccount.objects.filter(email__iexact=identifier).first() 
#                     # or UserAccount.objects.filter(username__iexact=identifier).first()
#                 if u and password and u.check_password(password):
#                     user = u

#         if not user:
#             raise AuthenticationFailed('Invalid credentials')

#         # Determine tenant context and enforce membership if logging in inside a specific tenant
#         tenant = getattr(request, 'tenant', None)
#         public_name = get_public_schema_name()

#         # If login is inside a tenant that is not the public schema, ensure user is a member
#         if tenant and tenant.schema_name != public_name:
#             with schema_context(public_name):
#                 if not UserAccount.objects.filter(pk=user.pk, tenants=tenant).exists():
#                     raise AuthenticationFailed('User is not a member of this tenant')

#         # Proceed with standard token creation
#         data = super().validate(attrs)
#         data['user'] = {'id': user.id, 'email': user.email, 'tenant': tenant.schema_name if tenant else None}

#         # If no tenant context or the context is the public schema, return the list of tenant
#         # memberships for this user (central login). Otherwise, include the specific tenant.
#         # Also accept an explicit `tenant_schema` in the login payload to request a token
#         # for a specific tenant when authenticating from the central/public endpoint.
#         requested_schema = None
#         if request is not None:
#             requested_schema = request.data.get('tenant_schema') or request.data.get('tenant') or request.data.get('tenant_id')

#         if requested_schema:
#             with schema_context(public_name):
#                 requested_tenant = Tenant.objects.filter(schema_name=requested_schema).first()
#                 if not requested_tenant:
#                     raise AuthenticationFailed('Requested tenant not found')
#                 # Ensure membership
#                 if not UserAccount.objects.filter(pk=user.pk, tenants=requested_tenant).exists():
#                     raise AuthenticationFailed('User is not a member of the requested tenant')
#                 data['tenant'] = {'id': requested_tenant.id, 'schema_name': requested_tenant.schema_name}
#                 return data

#         if not tenant or tenant.schema_name == public_name:
#             with schema_context(public_name):
#                 memberships = []
#                 # Exclude the public schema from the membership list
#                 qs = user.tenants.exclude(schema_name=public_name).all()
#                 for t in qs:
#                     memberships.append({'id': t.id, 'schema_name': t.schema_name, 'name': getattr(t, 'name', None)})
#                 data['tenants'] = memberships
#         else:
#             data['tenant'] = {'id': tenant.id, 'schema_name': tenant.schema_name}

#         return data