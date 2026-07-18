# tenants/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from tenant_users.tenants.models import TenantBase, UserProfile
# from inventory.models import TimeStampedModel


class UserAccount(UserProfile):
    pass


class Tenant(TenantBase):
    name = models.CharField(max_length=100)
    paid_until = models.DateField(null=True)
    on_trial = models.BooleanField(default=True)
    grace_until = models.DateField(null=True, blank=True)


class Domain(DomainMixin):
    pass
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)  # Basic, Pro
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField()  # 30, 365
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
class TenantPayment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="ETB")  # e.g., ETB, USD
    provider = models.CharField(max_length=50, blank=True, null=True)  # stripe, chapa, paystack
    reference = models.CharField(max_length=100, unique=True,blank=True, null=True, help_text="Unique payment reference from the payment provider ex: transaction id")
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("paid_verified", "Paid & Verified"),
            ("failed", "Failed"),

        ],
        default="pending",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount} for {self.tenant.name} on {self.reference}"


class Notification(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"Notification for {self.tenant.name}: {self.title}"


# class TenantPayment(models.Model):
#     tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     method = models.CharField(max_length=50)
#     status = models.CharField(
#         max_length=20,
#         choices=[
#             ("pending", "Pending"),
#             ("paid", "Paid"),
#             ("failed", "Failed"),
#         ],
#         default="pending",
#     )
#     paid_at = models.DateTimeField(null=True, blank=True)
#     expires_at = models.DateField(null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return f"Payment of {self.amount} for {self.tenant.name} on {self.created_at}"