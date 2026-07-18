# multi_inventory_check/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multi_inventory_check.settings")

app = Celery("multi_inventory_check")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
