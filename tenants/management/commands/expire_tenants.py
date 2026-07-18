from django.core.management.base import BaseCommand
from django.utils.timezone import now
from tenants.models import Tenant

class Command(BaseCommand):
    help = "Expire unpaid tenants after grace period"

    def handle(self, *args, **kwargs):
        today = now().date()

        expired = Tenant.objects.filter(
            paid_until__lt=today,
            grace_until__lt=today,
            on_trial=False
        )

        count = expired.count()

        # expired.update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"{count} tenants expired"
        ))
