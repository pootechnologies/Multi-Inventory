import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','multi_inventory_check.settings')
import django
django.setup()
from django.db import connection
from django_tenants.utils import schema_context

for schema in ('public','supermarket','tenant1'):
    with schema_context(schema):
        print('\nSchema:', schema)
        print(connection.introspection.table_names())
