from django.utils import timezone
from datetime import timedelta
import uuid
from rest_framework import serializers
from .models import Tenant, Domain, UserAccount, SubscriptionPlan, TenantPayment 
from django.core.management import call_command
from django_tenants.utils import schema_context, tenant_context, get_public_schema_name
from django.conf import settings
from django.db import transaction, IntegrityError
from django.contrib.auth.models import Group, Permission
from tenant_users.tenants.utils import create_public_tenant
from tenant_users.tenants.tasks import provision_tenant


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'duration_days', 'is_active']
class ChapaInitSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(),
        required=True
    )
    tenant = serializers.CharField( 
        read_only=True)
    subscriptionPlan = SubscriptionPlanSerializer(source='plan', read_only=True)
    provider = serializers.CharField(
        read_only=True)
class ChapaVerifySerializer(serializers.Serializer):
    # reference = serializers.CharField(required=True)
    class Meta:
        model = TenantPayment
        fields = ['id','plan']      
class PaymentInitSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    plan = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(),
        required=True
    )
    tenant = serializers.CharField( 
        read_only=True)
    subscriptionPlan = SubscriptionPlanSerializer(source='plan', read_only=True)
    provider = serializers.CharField(
        read_only=True)
    status = serializers.CharField(read_only=True)
    
class PaymentVerifySerializer(serializers.Serializer):
    reference = serializers.CharField(required=True)    
class PaymentInitUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantPayment
        # fields = ['id', 'status', 'paid_at', 'expires_at']
        fields = '__all__'

        def update(self, instance, validated_data):
            
            status = validated_data.get('status')
            
            if instance.status == 'pending' and status == 'paid' and not instance.reference:
                
                instance.reference = str(uuid.uuid4())
                instance.status = status
            instance.save()
            return instance


class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ['id', 'username', 'email', 'is_superuser']
 
# class GroupSerializer(serializers.ModelSerializer):
#     permissions = serializers.PrimaryKeyRelatedField(   
#         queryset=Permission.objects.filter(content_type__app_label__in=['tenants', 'tenant_users', 'inventory']),
#         many=True,
#         required=False
#     )
#     class Meta:
#         model = Group
#         fields = ['id', 'name', 'permissions']

#     def validate_permissions(self, value):
#         allowed_apps = ['tenants', 'tenant_users', 'inventory']
#         errors = []
#         for perm_str in value:
#             if '.' not in perm_str:
#                 errors.append('Permission strings must be in format "app_label.codename"')
#                 continue
#             app_label, codename = perm_str.split('.', 1)
#             if app_label not in allowed_apps:
#                 errors.append(f'App "{app_label}" is not allowed. Allowed apps: {allowed_apps}')
#                 continue
#             # ensure the permission actually exists
#             perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
#             if not perm:
#                 errors.append(f'Permission not found: {perm_str}')

#         if errors:
#             raise serializers.ValidationError({'permissions': errors})
#         return value

#     def create(self, validated_data):
#         perms = validated_data.pop('permissions', []) or []
#         group, created = Group.objects.get_or_create(name=validated_data['name'])
#         if perms:
#             group.permissions.clear()
#             for perm_str in perms:
#                 app_label, codename = perm_str.split('.', 1)
#                 perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
#                 if not perm:
#                     raise serializers.ValidationError({'permissions': f'Permission not found: {perm_str}'})
#                 group.permissions.add(perm)
#         group.save()
#         return group

#     def to_representation(self, instance):
#         rep = super().to_representation(instance)
#         rep['permissions'] = [f"{p.content_type.app_label}.{p.codename}" for p in instance.permissions.all()]
#         return rep

class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]

    def validate_permissions(self, permissions):
        allowed_apps = ["tenants", "tenant_users", "inventory"]

        permission_objects = []

        for perm in permissions:
            try:
                app_label, codename = perm.split(".", 1)
            except ValueError:
                raise serializers.ValidationError(
                    f'Permission "{perm}" must be in the format "app_label.codename".'
                )

            if app_label not in allowed_apps:
                raise serializers.ValidationError(
                    f'"{app_label}" is not an allowed app.'
                )

            try:
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
            except Permission.DoesNotExist:
                raise serializers.ValidationError(
                    f'Permission "{perm}" does not exist.'
                )

            permission_objects.append(permission)

        return permission_objects

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)

        instance.name = validated_data.get("name", instance.name)
        instance.save()

        if permissions is not None:
            instance.permissions.set(permissions)

        return instance

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "name": instance.name,
            "permissions": [
                f"{p.content_type.app_label}.{p.codename}"
                for p in instance.permissions.all()
            ]
        }
class OwnerCreateSerializer(serializers.Serializer):
    # username = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    # is_superuser = serializers.BooleanField(required=False, default=True)
    # is_staff = serializers.BooleanField(required=False, default=True)
    # groups = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, data):
        # Require a non-empty password when creating owner via API
        pwd = data.get('password')
        if not pwd:
            raise serializers.ValidationError({
                'password': 'Password is required for owner creation.'
            })
        return data

    # def create(self, validated_data):
    #     password = validated_data.pop('password', None)
    #     email = validated_data.get('email')
    #     return UserAccount.objects.create_user(email=email, password=password, **validated_data)
# class TenantSerializer(serializers.ModelSerializer):
#     # Accept an owner dict on write; we'll create the public user before tenant
#     owner = serializers.DictField(write_only=True, required=False)

#     class Meta:
#         model = Tenant
#         fields = [
#             'id', 
#             'name', 
#             'schema_name',
#             'paid_until', 
#             'on_trial',
#             # 'domain',
#             'owner',
#             ]

#     def create(self, validated_data):
#         # Handle nested owner creation (public user)
#         owner_data = validated_data.pop('owner', None)
#         if owner_data:
#             email = owner_data.get('email') or owner_data.get('username')
#             password = owner_data.get('password')
#             extra = {}
#             if 'username' in owner_data:
#                 extra['username'] = owner_data.get('username')

#             # If a user with this email exists, update their tenant permissions
#             owner_obj = UserAccount.objects.filter(email=email).first()
#             if owner_obj:
#                 try:
#                     # Ensure we're operating in the public schema when touching public-user related data
#                     with schema_context(get_public_schema_name()):
#                         utp = owner_obj.usertenantpermissions
#                         utp.is_superuser = True
#                         utp.is_staff = True
#                         utp.save(update_fields=["is_superuser", "is_staff"])
#                 except Exception:
#                     # best-effort: if tenant-perms object missing, ignore
#                     pass
#             else:
#                 # Create as superuser in public schema so manager logic can link public tenant
#                 with schema_context(get_public_schema_name()):
#                     owner_obj = UserAccount.objects.create_superuser(password=password, email=email, **extra)

#             validated_data['owner'] = owner_obj

#         tenant = Tenant.objects.create(**validated_data)
#         domain_name = f"{tenant.schema_name}.localhost"

#         # Create the domain first so any commands looking for the domain can find it
#         if domain_name:
#             Domain.objects.create(tenant=tenant, domain=domain_name, is_primary=True)

#         # Run tenant migrations for this schema. Try both common option names
#         try:
#             try:
#                 call_command('migrate_schemas', schema_name=tenant.schema_name, interactive=False, verbosity=0)
#             except Exception:
#                 # fallback to alternative option name used by some versions
#                 call_command('migrate_schemas', schema=tenant.schema_name, interactive=False, verbosity=0)
#         except Exception as exc:
#             # If migrations fail, raise a validation error so API returns 400 instead of 500
#             raise serializers.ValidationError({
#                 'non_field_errors': f'Tenant migrations failed: {exc}'
#             })

#         # with schema_context(tenant.schema_name):
#         #     # Create a default admin user for the new tenant
#         #     if not UserAccount.objects.filter(username= tenant.schema_name + '_admin').exists():
#         #         UserAccount.objects.create_superuser(
#         #             username= tenant.schema_name + '_admin',
#         #             email=f"admin@{tenant.name.lower()}.com",
#         #             password='admin123'
#         #         )

#         return tenant

    def to_representation(self, instance):
        """Include nested owner representation in the output."""
        rep = super().to_representation(instance)
        try:
            rep['owner'] = userSerializer(instance.owner).data
        except Exception:
            rep['owner'] = None
        return rep


class PublicTenantBootstrapSerializer(serializers.Serializer):
    # subdomain = serializers.CharField(required=True, write_only=True)
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True, required=False, allow_blank=True, help_text="The name of the tenant/company.")
    schema_name = serializers.CharField(required=False, allow_blank=True, read_only=True)
    # owner = OwnerCreateSerializer()
    campany_name = serializers.CharField(
    required=True,
    write_only=True,
    help_text="The name of the tenant/company."
          )
    owner = OwnerCreateSerializer()

    def validate_campany_name(self, value):
        return value.lower().replace(" ", "")

    def validate(self, data):
        # Only allow bootstrapping if public tenant does not already exist
        public_name = getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')
        if Tenant.objects.filter(schema_name=public_name).exists():
            raise serializers.ValidationError({
                'non_field_errors': 'Public tenant already exists; bootstrap is not allowed.'
            })
        return data

    def create(self, validated_data):
        owner = validated_data.get('owner')
        subdomain = validated_data.get('campany_name')
        # Call tenant_users helper to create public tenant and root user
        try:
            with transaction.atomic():
                public_tenant, public_domain, root_user = create_public_tenant(
                    domain_url=getattr(settings, 'BASE_DOMAIN', 'localhost'),
                    tenant_extra_data={"slug": subdomain},
                    first_name=owner.get('first_name'),
                    last_name=owner.get('last_name'),
                    owner_email=owner.get('email'),
                    phone_number=owner.get('phone_number'),
                    is_superuser=True,
                    is_staff=True,
                    password=owner.get('password'),
                    is_verified=True,
                )
        except IntegrityError:
            raise serializers.ValidationError({'non_field_errors': 'Failed to bootstrap public tenant: integrity error.'})

        return public_tenant


class ProvisionTenantSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True, required=False, allow_blank=True, help_text="The name of the tenant/company.")
    # subdomain = serializers.CharField(write_only=True)
    schema_name = serializers.CharField(read_only=True, required=False, allow_blank=True)
    # owner = OwnerCreateSerializer()
    # make campany_name lowercase to avoid confusion with name field 
    campany_name = serializers.CharField(
    required=True,
    write_only=True,
    help_text="The name of the tenant/company."
          )
    paid_until = serializers.DateField(read_only=True, required=False)
    on_trial = serializers.BooleanField(default=True)
    owner = OwnerCreateSerializer()

    def validate_campany_name(self, value):
        return value.lower().replace(" ", "")
    

    def validate(self, data):
        schema_name = data.get('campany_name')
        # Prevent duplicate schema_name
        if Tenant.objects.filter(schema_name=schema_name).exists():
            raise serializers.ValidationError({
                'schema_name': 'A tenant with this schema_name already exists.'
            })

        # Prevent duplicate domain for the chosen subdomain
        base = getattr(settings, 'BASE_DOMAIN', 'localhost')
        domain_name = f"{data.get('campany_name')}.{base}"
        if Domain.objects.filter(domain=domain_name).exists():
            raise serializers.ValidationError({
                'subdomain': 'A tenant with this subdomain/domain already exists.'
            })
        # prvent duplicate owner email across tenants
        owner_email = data.get('owner', {}).get('email')
        if Tenant.objects.filter(owner__email=owner_email).exists():
            raise serializers.ValidationError({
                'owner': 'A tenant with this owner email already exists.'
            })

        return data

    def create(self, validated_data):
        name = validated_data.get('campany_name')
        subdomain = validated_data.get('campany_name')
        schema_name = validated_data.get('campany_name')
        # paid_until = validated_data.get('paid_until')
        on_trial = validated_data.get('on_trial')
        owner_data = validated_data.get('owner')

        # Create tenant owner in public schema
        with schema_context(get_public_schema_name()):
            tenant_owner = None
            tenant_owner = UserAccount.objects.filter(email=owner_data.get('email')).first()
            if not tenant_owner:
                tenant_owner = UserAccount.objects.create_user(
                    first_name=owner_data.get('first_name'),
                    last_name=owner_data.get('last_name'),
                    phone_number=owner_data.get('phone_number'),
                    email=owner_data.get('email'),
                    password=owner_data.get('password'),
                )
                tenant_owner.is_verified = True
                tenant_owner.save()

        #if on_trial is true: give 7 days trial period
        #    paid_until = timezone.now().date() + timezone.timedelta(days=14)
        #  else:
        #   paid_until = None
        if not on_trial:
            on_trial = True

        if on_trial:
            paid_until = timezone.now().date() + timezone.timedelta(days=7)
        elif not on_trial and not paid_until:
            paid_until = None

        # Provision tenant using tenant_users task helper
        try:
            with transaction.atomic():
                tenant_obj, domain_obj = provision_tenant(
                    tenant_name=name,
                    tenant_extra_data={'paid_until': paid_until, 'on_trial': on_trial},                  
                    tenant_slug=subdomain,
                    schema_name=schema_name,
                    owner=tenant_owner,
                    is_superuser=True,
                    is_staff=True,
                )
        except IntegrityError:
            raise serializers.ValidationError({
                'non_field_errors': 'Tenant provisioning failed due to integrity error (possible duplicate created concurrently).'
            })
        except Exception as exc:
            raise serializers.ValidationError({
                'non_field_errors': f'Tenant provisioning failed: {exc}'
            })

        # Add tenant owner to the new tenant with requested roles and groups
        try:
            role_super = owner_data.get('is_superuser', True)
            role_staff = owner_data.get('is_staff', True)
            # add_user will switch into tenant schema internally; only call it if user not already
            # attached to the tenant. If the user was already added by the provisioner, just update
            # their tenant-permissions (roles) and groups.
            already_member = False
            with schema_context(get_public_schema_name()):
                already_member = tenant_owner.tenants.filter(pk=tenant_obj.pk).exists()

            if not already_member:
                tenant_obj.add_user(tenant_owner, is_superuser=role_super, is_staff=role_staff)
            else:
                # ensure tenant-permission flags updated inside tenant schema
                with schema_context(tenant_obj.schema_name):
                    try:
                        utp = tenant_owner.usertenantpermissions
                        utp.is_superuser = role_super
                        utp.is_staff = role_staff
                        utp.save(update_fields=['is_superuser', 'is_staff'])
                    except Exception:
                        # if utp missing for some reason, try to (re)create via add_user
                        tenant_obj.add_user(tenant_owner, is_superuser=role_super, is_staff=role_staff)

            # add groups inside tenant schema
            groups = owner_data.get('groups', []) or []
            if groups:
                with schema_context(tenant_obj.schema_name):
                    utp = tenant_owner.usertenantpermissions
                    for gname in groups:
                        grp, _ = Group.objects.get_or_create(name=gname)
                        utp.groups.add(grp)
                    utp.save()
        except Exception as exc:
            # best-effort cleanup: try to remove tenant if critical failure
            raise serializers.ValidationError({
                'non_field_errors': f'Failed assigning roles/groups to tenant owner: {exc}'
            })

        # Optionally add the public root user to the new tenant if public tenant exists
        try:
            public_tenant = Tenant.objects.get(schema_name=getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public'))
            root_user = public_tenant.owner
            tenant_obj.add_user(root_user, is_superuser=True, is_staff=True)
        except Exception:
            pass

        return tenant_obj


class TenantUserCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    # username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    is_superuser = serializers.BooleanField(default=False)
    is_staff = serializers.BooleanField(default=False)
    groups = serializers.ListField(child=serializers.CharField(), required=False)
    tenant_groups = serializers.SerializerMethodField()

    def validate(self, data):
        if not data.get('password'):
            raise serializers.ValidationError({'password': 'Password is required.'})
        # prvent duplicate email across tenants
        email = data.get('email')
        if UserAccount.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        
        return data
    
    def _tenant_perms(self, obj):
        tenant = self.context['request'].tenant
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            try:
                utp = obj.usertenantpermissions
                return utp
            except Exception:
                return None
    def get_tenant_groups(self, obj):
        utp = self._tenant_perms(obj)
        if not utp:
            return []
        return [g.name for g in utp.groups.all()]
    

class TenantUserUpdateSerializer(serializers.Serializer):
    # username = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    is_superuser = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)
    # is_active = serializers.BooleanField(required=False)
    # is_verified = serializers.BooleanField(required=False)
    tenant_groups = serializers.ListField(child=serializers.CharField(), required=False)

    def update(self, instance, validated_data):
        # `instance` is the public UserAccount object
        tenant = self.context.get('tenant') or self.context['request'].tenant

        # Update public profile in public schema
        print(instance.email)
        with schema_context(get_public_schema_name()):
            if 'first_name' in validated_data:
                instance.first_name = validated_data['first_name']
            if 'last_name' in validated_data:
                instance.last_name = validated_data['last_name']
            if 'phone_number' in validated_data:
                instance.phone_number = validated_data['phone_number']    
            if 'email' in validated_data:
                instance.email = validated_data['email']
            if 'password' in validated_data:
                instance.set_password(validated_data['password'])
            instance.save()

        # Update tenant-permissions inside tenant schema
        with schema_context(tenant.schema_name):
            try:
                utp = instance.usertenantpermissions
            except Exception:
                raise serializers.ValidationError({'non_field_errors': 'User not on this tenant'})

            if 'is_superuser' in validated_data:
                utp.is_superuser = validated_data['is_superuser']
            if 'is_staff' in validated_data:
                utp.is_staff = validated_data['is_staff']
            # if 'is_active' in validated_data:
            #     utp.is_active = validated_data['is_active']
            # if 'is_verified' in validated_data:
            #     utp.is_verified = validated_data['is_verified']

            if 'tenant_groups' in validated_data:
                utp.groups.clear()
                from django.contrib.auth.models import Group
                for gname in validated_data['tenant_groups'] or []:
                    grp, _ = Group.objects.get_or_create(name=gname)
                    utp.groups.add(grp)

            utp.save()

        return instance
   
class TenantUserDetailedSerializer(serializers.ModelSerializer):
    tenant_is_superuser = serializers.SerializerMethodField()
    tenant_is_staff = serializers.SerializerMethodField()
    tenant_groups = serializers.SerializerMethodField()

    class Meta:
        model = UserAccount
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'tenant_is_superuser', 'tenant_is_staff', 'tenant_groups',
        ]

    def _get_tenant(self):
        tenant = self.context.get('tenant') if self.context else None
        if not tenant and self.context and self.context.get('request'):
            tenant = getattr(self.context['request'], 'tenant', None)
        return tenant

    def _get_tenant_perms(self, obj):
        tenant = self._get_tenant()
        if not tenant:
            return None
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            try:
                return obj.usertenantpermissions
            except Exception:
                return None

    def get_tenant_is_superuser(self, obj):
        utp = self._get_tenant_perms(obj)
        return bool(getattr(utp, 'is_superuser', False))

    def get_tenant_is_staff(self, obj):
        utp = self._get_tenant_perms(obj)
        return bool(getattr(utp, 'is_staff', False))

    def get_tenant_groups(self, obj):
        utp = self._get_tenant_perms(obj)
        if not utp:
            return []
        return [g.name for g in utp.groups.all()]