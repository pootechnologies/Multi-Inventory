# tenants/tasks.py
from celery import shared_task
from datetime import timedelta
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings

from tenants.models import Tenant
from .utils import notify_tenant


@shared_task
def send_subscription_reminders():
    today = now().date()
    reminder_until = today + timedelta(days=3)

    tenants = Tenant.objects.filter(
        paid_until__range=(today, reminder_until),
        on_trial=False
    )

    for tenant in tenants:
        if not tenant.owner or not tenant.owner.email:
            continue

        days_left = (tenant.paid_until - today).days

        title = "Subscription Expiry Reminder"
        message = f"Your subscription expires in {days_left} day(s)."

        # In-app notification
        notify_tenant(tenant, title, message)

        # Email (console backend in dev)
        send_mail(
            title,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [tenant.owner.email],
            fail_silently=True,
        )
    # print(f"Sent subscription reminders to {tenants.count()} tenants.")