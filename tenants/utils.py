# notifications/utils.py

from tenants.models import Notification 

def notify_tenant(tenant, title, message):
    Notification.objects.create(
        tenant=tenant,
        title=title,
        message=message
    )
