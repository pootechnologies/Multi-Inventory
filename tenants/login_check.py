# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import authenticate
# from django_tenants.utils import schema_context, get_public_schema_name
# from .models import UserAccount, Tenant


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         request = self.context.get('request')

#         # Authenticate user (backend may accept email or username)
#         identifier = attrs.get(self.username_field) or attrs.get('username') or attrs.get('email')
#         user = None
#         if identifier:
#             user = authenticate(request=request, username=identifier, password=attrs.get('password'))

#         # Fallback: if the auth backend couldn't authenticate (often due to tenant schema
#         # context differences), try to find the user in the public schema and verify password
#         # directly. This lets tenant users authenticate from the central endpoint by email.
#         if not user:
#             public_name = get_public_schema_name()
#             with schema_context(public_name):
#                 u = None
#                 if identifier:
#                     u = UserAccount.objects.filter(email__iexact=identifier).first() or UserAccount.objects.filter(username__iexact=identifier).first()
#                 if u and u.check_password(attrs.get('password')):
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


# class TenantTokenObtainPairView(TokenObtainPairView):
#     serializer_class = TenantTokenObtainPairSerializer
# # ///////////////////////////////////////////////////////////////////////////////////
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import authenticate
# from django_tenants.utils import schema_context, get_public_schema_name
# from .models import UserAccount, Tenant


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         request = self.context.get('request')

#         # Authenticate user (backend may accept email or username)
#         user = authenticate(request=request, username=attrs.get(self.username_field), password=attrs.get('password'))
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


# class TenantTokenObtainPairView(TokenObtainPairView):
#     serializer_class = TenantTokenObtainPairSerializer

# # //////////////////////////////////////////////////////////////////////////////////////////


# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import authenticate
# from django_tenants.utils import schema_context, get_public_schema_name
# from .models import UserAccount


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         request = self.context.get('request')

#         # Authenticate user (backend may accept email or username)
#         user = authenticate(request=request, username=attrs.get(self.username_field), password=attrs.get('password'))
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


# class TenantTokenObtainPairView(TokenObtainPairView):
#     serializer_class = TenantTokenObtainPairSerializer

# # //////////////////////////////////////////////////////////////////////////////////////////

# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework.exceptions import AuthenticationFailed
# from django.contrib.auth import authenticate
# from django_tenants.utils import schema_context, get_public_schema_name
# from .models import UserAccount


# class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         request = self.context.get('request')

#         # Authenticate user (backend may accept email or username)
#         user = authenticate(request=request, username=attrs.get(self.username_field), password=attrs.get('password'))
#         if not user:
#             raise AuthenticationFailed('Invalid credentials')

#         # If a tenant context exists on the request, ensure the user belongs to that tenant
#         tenant = getattr(request, 'tenant', None)
#         if tenant:
#             # Tenant membership is recorded in the public schema; check membership there
#             with schema_context(get_public_schema_name()):
#                 if not UserAccount.objects.filter(pk=user.pk, tenants=tenant).exists():
#                     raise AuthenticationFailed('User is not a member of this tenant')

#         # Proceed with standard token creation
#         data = super().validate(attrs)
#         data['user'] = {'id': user.id, 'email': user.email, 'tenant': tenant.schema_name}
#         if tenant:
#             data['tenant'] = {'id': tenant.id, 'schema_name': tenant.schema_name}
#         return data


# class TenantTokenObtainPairView(TokenObtainPairView):
#     serializer_class = TenantTokenObtainPairSerializer

# # //////////////////////////////////////////////////////////////////////////////////////////

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
