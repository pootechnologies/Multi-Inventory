from django.urls import reverse
from django.test import TestCase, Client
from django.conf import settings
from .models import Tenant, Domain, UserAccount
from django_tenants.utils import get_public_schema_name, schema_context


class TenantAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Ensure database migrated; tests run in default (public) schema

    def test_bootstrap_public_tenant(self):
        url = reverse('bootstrap-public')
        payload = {
            "subdomain": "public",
            "owner": {"email": "system@localhost", "password": "admin123"}
        }
        resp = self.client.post(url, data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        # response should include tenant data with schema_name public
        tenant_data = body.get('tenant')
        self.assertIsNotNone(tenant_data)
        self.assertEqual(tenant_data.get('schema_name'), getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public'))
        # public tenant should exist in DB
        self.assertTrue(Tenant.objects.filter(schema_name=getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')).exists())

    def test_provision_tenant_and_prevent_duplicates(self):
        # First, ensure a public tenant exists (create minimal one)
        public_schema = getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')
        if not Tenant.objects.filter(schema_name=public_schema).exists():
            sys = UserAccount(email='system@localhost', is_active=True)
            sys.set_password('admin123')
            sys.save()
            public = Tenant(schema_name=public_schema, name='Public Tenant', owner=sys)
            public.save()
            Domain.objects.create(domain=getattr(settings, 'BASE_DOMAIN', 'localhost'), tenant=public, is_primary=True)

        url = reverse('provision-tenant')
        payload = {
            "name": "Tenant 1",
            "subdomain": "tenant1",
            "schema_name": "tenant1",
            "owner": {"email": "admin@tenant1.localhost", "password": "password"}
        }
        # provision first time -> success
        resp1 = self.client.post(url, data=payload, content_type='application/json')
        self.assertEqual(resp1.status_code, 201)

        # Try to provision again with same schema_name -> should return 400 and include an error
        resp2 = self.client.post(url, data=payload, content_type='application/json')
        self.assertEqual(resp2.status_code, 400)
        body2 = resp2.json()
        # Expect either schema_name error or non_field_errors
        self.assertTrue('schema_name' in body2 or 'non_field_errors' in body2 or 'subdomain' in body2)

    def test_tenant_owner_can_create_tenant_user_with_roles_and_groups(self):
        # ensure public tenant exists
        public_schema = getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')
        if not Tenant.objects.filter(schema_name=public_schema).exists():
            sys = UserAccount(email='system@localhost', is_active=True)
            sys.set_password('admin123')
            sys.save()
            public = Tenant(schema_name=public_schema, name='Public Tenant', owner=sys)
            public.save()
            Domain.objects.create(domain=getattr(settings, 'BASE_DOMAIN', 'localhost'), tenant=public, is_primary=True)

        # provision a tenant via API
        prov_url = reverse('provision-tenant')
        prov_payload = {
            "name": "Tenant X",
            "subdomain": "tenantx",
            "schema_name": "tenantx",
            "owner": {"email": "owner@tenantx.local", "password": "ownerpass"}
        }
        resp = self.client.post(prov_url, data=prov_payload, content_type='application/json')
        self.assertEqual(resp.status_code, 201)

        tenant = Tenant.objects.get(schema_name='tenantx')
        tenant_owner = UserAccount.objects.get(email='owner@tenantx.local')

        # login as tenant_owner
        self.client.force_login(tenant_owner)

        # create a tenant user
        url = reverse('tenant-user-create')
        payload = {
            "email": "alice@tenantx.local",
            "username": "alice",
            "password": "alicepass",
            "is_superuser": False,
            "is_staff": True,
            "groups": ["Manager", "Sales"]
        }
        # Make request with Host header so tenant middleware sets request.tenant
        resp2 = self.client.post(url, data=payload, content_type='application/json', HTTP_HOST=f"{tenant.schema_name}.{getattr(settings,'BASE_DOMAIN','localhost')}")
        self.assertEqual(resp2.status_code, 201)

        # Verify tenant-user permissions and groups inside tenant schema
        with schema_context(tenant.schema_name):
            new_user = UserAccount.objects.get(email='alice@tenantx.local')
            utp = new_user.usertenantpermissions
            self.assertFalse(utp.is_superuser)
            self.assertTrue(utp.is_staff)
            group_names = set(g.name for g in utp.groups.all())
            self.assertTrue('Manager' in group_names and 'Sales' in group_names)
