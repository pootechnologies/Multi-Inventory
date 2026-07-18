from django.utils.timezone import now
from django.http import JsonResponse

class TenantPaymentRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)

        if tenant and tenant.schema_name != "public":
            today = now().date()

            # exclude init payment 
            if request.path.startswith('/api/init-payment/'):
                return self.get_response(request)
            if request.path.startswith('/api/payments-verify/'):
                return self.get_response(request)
            if request.path.startswith('/api/chapa-initiate/'):
                return self.get_response(request)
            if request.path.startswith('/api/chapa-verify/<str:reference>/'):
                return self.get_response(request)

            
            if tenant.on_trial and tenant.paid_until and tenant.paid_until <= today:
                tenant.on_trial = False
                tenant.save()

            if tenant.on_trial:
                return self.get_response(request)
                
            if tenant.paid_until and tenant.paid_until >= today:
                return self.get_response(request)

            if tenant.grace_until and tenant.grace_until >= today:
                return self.get_response(request)

            return JsonResponse(
                {"detail": "Subscription expired. Please renew."},
                status=402
            )

        return self.get_response(request)
