import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multi_inventory_check.settings')
import django
django.setup()
from tenants.models import Tenant, Domain

t = Tenant(schema_name='tenant1', name='Tenant 1')
t.save()
Domain.objects.create(domain='tenant1.localhost', tenant=t, is_primary=True)
print('CREATED', t.schema_name)
