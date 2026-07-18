# # from django.core.management.base import BaseCommand
# # from django.core.mail import send_mail
# # from django.utils.timezone import now
# # from datetime import timedelta
# # from multi_inventory_check.settings import DEFAULT_FROM_EMAIL
# # from tenants.models import Tenant

# # class Command(BaseCommand):
# #     help = "Send expiry reminders to tenants whose subscriptions are about to expire"

# #     def handle(self, *args, **kwargs):
# #         today = now().date()
# #         reminder_date = today + timedelta(days=3)

# #         tenants_to_notify = Tenant.objects.filter(
# #             paid_until=reminder_date,
# #             on_trial=False
# #         )

# #         for tenant in tenants_to_notify:
# #             # Send email reminder
# #             subject = "Subscription Expiry Reminder"
# #             message = f"Dear {tenant.name},\n\nYour subscription is set to expire on {tenant.paid_until}. Please renew your subscription to continue enjoying our services.\n\nBest regards,\nYour Company"
# #             if tenant.owner and tenant.owner.email:
# #                recipient_list = [tenant.owner.email]  # Assuming Tenant has an owner_email field
# #                print(f"Sending expiry reminder to {tenant.owner.email} for tenant {tenant.name}")
# #             if not tenant.owner.email:
# #                 raise ValueError(f"No email found for tenant owner of {tenant.name}")   

# #             send_mail(
# #                     subject,
# #                     message,
# #                     DEFAULT_FROM_EMAIL,
# #                     recipient_list,
# #                     fail_silently=False,
# #                       )


from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
from tenants.models import Tenant


# class Command(BaseCommand):
#     help = "Send expiry reminders to tenants whose subscriptions are about to expire"

#     def handle(self, *args, **kwargs):
#         today = now().date()
#         reminder_date = today + timedelta(days=3)

#         tenants_to_notify = Tenant.objects.filter(
#             paid_until=reminder_date,
#             on_trial=False
#         )

#         for tenant in tenants_to_notify:
#             if not tenant.owner or not tenant.owner.email:
#                 self.stdout.write(
#                     self.style.WARNING(
#                         f"Skipping tenant {tenant.name}: no owner email"
#                     )
#                 )
#                 continue

#             subject = "Subscription Expiry Reminder"
#             message = (
#                 f"Dear {tenant.name},\n\n"
#                 f"Your subscription is set to expire on {tenant.paid_until}. "
#                 f"Please renew your subscription to continue enjoying our services.\n\n"
#                 f"Best regards,\nYour Company"
#             )

#             self.stdout.write(
#                 f"Sending expiry reminder to {tenant.owner.email} "
#                 f"for tenant {tenant.name}"
#             )

#             send_mail(
#                 subject,
#                 message,
#                 settings.DEFAULT_FROM_EMAIL,
#                 [tenant.owner.email],
#                 fail_silently=False,
#             )
#             print("🔥 send_expiry_reminders command loaded")

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        today = now().date()
        reminder_until = today + timedelta(days=3)

        tenants_to_notify = Tenant.objects.filter(
            paid_until__range=(today, reminder_until),
            on_trial=False
        )

        self.stdout.write(
            f"Sending reminders to {tenants_to_notify.count()} tenants"
        )

        for tenant in tenants_to_notify:
            if not tenant.owner or not tenant.owner.email:
                continue

            send_mail(
                "Subscription Expiry Reminder",
                f"Dear {tenant.name}, your subscription expires on {tenant.paid_until}.",
                settings.DEFAULT_FROM_EMAIL,
                [tenant.owner.email],
            )

            self.stdout.write(
                f"✔ Reminder sent to {tenant.owner.email}"
            )
