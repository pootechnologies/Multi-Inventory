import requests
import json
import hmac
import hashlib
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import uuid
# import settings
from multi_inventory_check.settings import CHAPA_PUBLIC_KEY, CHAPA_BASE_URL, CHAPA_SECRET_KEY, CHAPA_VERIFY_URL
from django.utils import timezone
from datetime import timedelta
from django.http import Http404, JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SubscriptionPlan, Tenant, UserAccount, TenantPayment
from .user_permission import IsTenantOwnerOrAdmin, IsTenantUser, HasModelPermissionForTenant, HasTenantPermission
from django_tenants.utils import get_public_schema_name, schema_context
from django.contrib.auth.models import Group, Permission
from inventory.views import Pagination

from .serializers import (
    PublicTenantBootstrapSerializer,
    ProvisionTenantSerializer,
    TenantUserCreateSerializer,
    GroupSerializer,
    PaymentInitSerializer,
    PaymentInitUpdateSerializer,
    PaymentVerifySerializer, 
    ChapaInitSerializer,
    ChapaVerifySerializer,SubscriptionPlanSerializer,
    # TenantSerializer, 
    TenantUserUpdateSerializer, userSerializer, TenantUserDetailedSerializer
)
from django.db import IntegrityError, transaction
import time
import logging


class ChapaPaymentInitView(generics.GenericAPIView):
    serializer_class = ChapaInitSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # plan = serializer.validated_data.get("plan", None)

        # Fetch the subscription plan
        try:
            # plan = SubscriptionPlan.objects.get(id=plan_id)
            plan = serializer.validated_data.get("plan", None)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Invalid plan ID"}, status=status.HTTP_400_BAD_REQUEST)
       
        tenant = request.tenant
        print(f"Tenant: {tenant}")
        if not tenant:
            return Response({"detail": "No tenant context"}, status=status.HTTP_400_BAD_REQUEST)
       
        # Prepare data for Chapa payment initiation
        # ensure we have a valid email to send to Chapa (Chapa validates format)
        owner_email = getattr(getattr(tenant, 'owner', None), 'email', None) or (getattr(request, 'user', None) and getattr(request.user, 'email', None))
        if not owner_email:
            return Response({"detail": "Tenant owner email not set; cannot initiate payment."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(owner_email)
        except DjangoValidationError:
            return Response({"detail": "Tenant owner email is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # Truncate customization title to 16 chars per Chapa validation
        customization_title = (plan.name or "Subscription")[:16]       

        reference = str(uuid.uuid4())
        callback_url = f"http://{tenant if tenant else 'default'}.localhost:8000/api/chapa-verify/{reference}/"  # Adjust as needed for your domain and route
        return_url = f"http://{tenant if tenant else 'default'}.localhost:8000/api/chapa-verify/{reference}/"  # Adjust as needed for your domain and route
        chapa_data = {
            "amount": str(plan.price),
            "currency": "ETB",
            "email": owner_email,
            
            "tx_ref": reference,
            # callback_url should point to your webhook that accepts Chapa POSTs
            "callback_url": callback_url,
            "return_url": return_url,
            # "return_url": settings.FRONTEND_PAYMENT_REDIRECT,
            "customization": {
                "title": customization_title,
                "description": plan.name
            }
        }

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        # Initiate payment with Chapa
        try:
            response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", json=chapa_data, headers=headers, timeout=10)
        except requests.RequestException as exc:
            return Response({"detail": "Failed to initiate payment with Chapa", "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not response.ok:
            try:
                body = response.json()
            except Exception:
                body = response.text
            return Response({"detail": "Failed to initiate payment with Chapa", "chapa_response": body, "status_code": response.status_code}, status=status.HTTP_502_BAD_GATEWAY)

        chapa_response = response.json()
        if chapa_response.get("status") != "success":
            return Response({"detail": "Chapa payment initiation failed", "chapa_response": chapa_response}, status=status.HTTP_400_BAD_REQUEST)

        payment = TenantPayment.objects.create(
            tenant=tenant,
            amount=plan.price,
            plan=plan,
            status="pending",
            reference=reference,  # Unique reference 
            provider="chapa"
        )
        tenant = payment.tenant
        tenant.paid_until = timezone.now().date() + timedelta(days=1)  # 1 day grace period
        tenant.save()

        payment_url = chapa_response.get("data", {}).get("checkout_url")

        return Response({
            "reference": payment.reference,
            "payment_url": payment_url
        }, status=status.HTTP_201_CREATED)
    
class ChapaPaymentVerifyView(generics.GenericAPIView):
        
    serializer_class = PaymentVerifySerializer
    def get(self, request, reference):
        # chapa payment verification


        try:
            payment = TenantPayment.objects.get(reference=reference)
            if not payment:
                return Response({"detail": "Invalid reference"}, status=status.HTTP_404_NOT_FOUND)
        except TenantPayment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)  



        headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
        try:
            response = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{reference}", headers=headers)
        except requests.RequestException as exc:
            return Response({"detail": "Failed to verify payment with Chapa", "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not response.ok:
            try:
                body = response.json()
            except Exception:
                body = response.text
            return Response({"detail": "Failed to verify payment with Chapa", "chapa_response": body, "status_code": response.status_code}, status=status.HTTP_502_BAD_GATEWAY)

        chapa_response = response.json()
        if chapa_response.get("status") != "success":
            # or chapa_response["data"]["status"] != "successful":
            return Response({"detail": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)
        

        data = chapa_response.get("data",{})
        if data.get("status") == "success" and float(data.get("amount", 0)) == float(payment.amount):            
            if payment.status != "paid_verified":
                payment.status = "paid_verified"
                payment.paid_at = timezone.now()
                # Safely compute expiry days
                days = payment.plan.duration_days if (payment.plan and getattr(payment.plan, 'duration_days', None) is not None) else 0
                payment.expires_at = timezone.now().date() + timedelta(days=days)
                payment.save()

                # Update tenant's paid_until date
                tenant = payment.tenant
                tenant.paid_until = payment.expires_at
                tenant.grace_until = tenant.paid_until + timedelta(days=3)  # 3 days grace period
                tenant.on_trial = False
                tenant.save()

    
            return Response({"detail": "Payment verified successfully", "chapa_response": chapa_response}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Payment verification failed", "chapa_response": chapa_response}, status=status.HTTP_400_BAD_REQUEST)    



    # def post(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     reference = serializer.validated_data["reference"]

    #     try:
    #         payment = TenantPayment.objects.get(reference=reference)
    #         if not payment:
    #             return Response({"detail": "Invalid reference"}, status=status.HTTP_404_NOT_FOUND)
    #         if payment.tenant != request.tenant:
    #             return Response({"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    #     except TenantPayment.DoesNotExist:
    #         return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

    #     headers = {
    #         # Use secret key for server-to-server verification
    #         "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
    #         "Content-Type": "application/json",
    #     }

    #     # Verify payment with Chapa (robust error handling and debug info)
    #     try:
    #         response = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=10)
    #     except requests.RequestException as exc:
    #         return Response({"detail": "Failed to verify payment with Chapa", "error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    #     if not response.ok:
    #         try:
    #             body = response.json()
    #         except Exception:
    #             body = response.text
    #         return Response({"detail": "Failed to verify payment with Chapa", "chapa_response": body, "status_code": response.status_code}, status=status.HTTP_502_BAD_GATEWAY)

    #     chapa_response = response.json()
    #     # Chapa may return data.status as 'success' (test) or 'successful' (live); accept both
    #     chapa_data_status = chapa_response.get("data", {}).get("status")
    #     if chapa_response.get("status") != "success" or chapa_data_status not in ("successful", "success"):
    #         return Response({"detail": "Payment verification failed", "chapa_response": chapa_response}, status=status.HTTP_400_BAD_REQUEST)

    #     # Update payment record
    #     if chapa_response.get("status") == "success" and chapa_data_status in ("successful", "success"):
    #         if payment.status != "paid_verified":
    #             payment.status = "paid_verified"
    #             payment.paid_at = timezone.now()
    #             # Safely compute expiry days
    #             days = payment.plan.duration_days if (payment.plan and getattr(payment.plan, 'duration_days', None) is not None) else 0
    #             payment.expires_at = timezone.now().date() + timedelta(days=days)
    #             payment.save()

    #             # Update tenant's paid_until date
    #             tenant = payment.tenant
    #             tenant.paid_until = payment.expires_at
    #             tenant.grace_until = tenant.paid_until + timedelta(days=3)  # 3 days grace period
    #             tenant.on_trial = False
    #             tenant.save()

    #     return Response({"detail": "Payment verified successfully"}, status=status.HTTP_200_OK)    


@csrf_exempt
def chapa_webhook(request):
    """Handle Chapa webhook callbacks.

    Expects JSON payload from Chapa. Will verify signature if
    `CHAPA_WEBHOOK_SECRET` is set in settings. It will then perform
    a server-to-server verify and update the `TenantPayment` record
    idempotently.
    """
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        payload = request.body or b'{}'
        data = json.loads(payload.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON payload'}, status=status.HTTP_400_BAD_REQUEST)

    # Optional signature verification
    webhook_secret = getattr(settings, 'CHAPA_WEBHOOK_SECRET', None)
    sig_header = request.META.get('HTTP_X_CHAPA_SIGNATURE') or request.META.get('HTTP_X_SIGNATURE')
    if webhook_secret and sig_header:
        expected = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            return JsonResponse({'detail': 'Invalid webhook signature'}, status=status.HTTP_400_BAD_REQUEST)

    # Extract tx_ref (our reference) or chapa reference
    tx_ref = data.get('tx_ref') or data.get('data', {}).get('tx_ref')
    chapa_reference = data.get('reference') or data.get('data', {}).get('reference')

    ref = tx_ref or chapa_reference
    if not ref:
        return JsonResponse({'detail': 'Missing reference in webhook payload'}, status=status.HTTP_400_BAD_REQUEST)

    # Try to find TenantPayment by our tx_ref first, then by chapa reference
    payment = None
    if tx_ref:
        payment = TenantPayment.objects.filter(reference=tx_ref).first()
    if not payment and chapa_reference:
        payment = TenantPayment.objects.filter(reference=chapa_reference).first()

    if not payment:
        # Nothing to update; return 200 so provider doesn't keep retrying
        return JsonResponse({'detail': 'Payment not found'}, status=status.HTTP_200_OK)

    # If already verified, respond 200
    if payment.status == 'paid_verified':
        return JsonResponse({'detail': 'Already verified'}, status=status.HTTP_200_OK)

    # Do server-to-server verify for extra safety
    headers = {
        'Authorization': f"Bearer {getattr(settings, 'CHAPA_SECRET_KEY', '')}",
    }
    try:
        resp = requests.get(f"{getattr(settings, 'CHAPA_BASE_URL', '')}/transaction/verify/{ref}", headers=headers, timeout=10)
        if not resp.ok:
            return JsonResponse({'detail': 'Chapa verify failed', 'status_code': resp.status_code}, status=status.HTTP_200_OK)
        chapa_resp = resp.json()
    except Exception:
        return JsonResponse({'detail': 'Chapa verification error'}, status=status.HTTP_200_OK)

    chapa_data_status = chapa_resp.get('data', {}).get('status')
    if chapa_resp.get('status') == 'success' and chapa_data_status in ('successful', 'success'):
        # mark payment
        payment.status = 'paid_verified'
        payment.paid_at = timezone.now()
        days = payment.plan.duration_days if (payment.plan and getattr(payment.plan, 'duration_days', None) is not None) else 0
        payment.expires_at = timezone.now().date() + timedelta(days=days)
        payment.save()

        tenant = payment.tenant
        tenant.paid_until = payment.expires_at
        tenant.grace_until = tenant.paid_until + timedelta(days=3)
        tenant.on_trial = False
        tenant.save()

    return JsonResponse({'detail': 'webhook processed'}, status=status.HTTP_200_OK)
    


# class NotificationListView(generics.ListAPIView):
#     # serializer_class = NotificationListSerializer

#     def get_queryset(self):
#         tenant = getattr(self.request, 'tenant', None)
#         return tenant.notifications.all() if tenant else Notification.objects.none()
class SubscriptionPlanListCreateView(generics.ListCreateAPIView):
    pagination_class = Pagination
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.order_by('id')
class SubscriptionPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.order_by('id')    

class InitPaymentListView(generics.ListAPIView):
    serializer_class = PaymentInitSerializer
    queryset = TenantPayment.objects.order_by('id')
    pagination_class = Pagination

class InitPaymentView(generics.ListCreateAPIView):
    serializer_class = PaymentInitSerializer
    queryset = TenantPayment.objects.order_by('id')
    pagination_class = Pagination
    # plan = SubscriptionPlan.objects.get(id=requests.data["plan_id"]) if "plan_id" in requests.data else None
    # AttributeError: module 'requests' has no attribute 'data'
    # plan = None
    def get(self, request, *args, **kwargs):
        tenant = request.tenant
        if tenant:
            payments = TenantPayment.objects.filter(tenant=tenant)
            serializer = PaymentInitSerializer(payments, many=True)
            return Response(serializer.data)
        # TypeError: InitPaymentView.get_queryset() missing 1 required positional argument: 'request'

        # return super().get_queryset()
    
    def create(self, request, *args, **kwargs):
        tenant = request.tenant
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data.get("plan", None)
        print("plan:", plan.price if plan else "No plan selected")

        payment = TenantPayment.objects.create(
            tenant=tenant,
            # amount=request.data["amount"],
            amount=plan.price,
            plan=plan,
            provider="local_init",
            # reference=str(uuid.uuid4()), # Generate a unique reference
            # reference=null,
            status="pending",
        )

        return Response({
            "reference": payment.reference,
            "payment_url": f"https://payment-gateway/pay/{payment.reference}"
        })
class InitPaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentInitUpdateSerializer
    queryset = TenantPayment.objects.order_by('id')

    # def update(self, request, *args, **kwargs):
    #     serializers = self.get_serializer( self.get_object(), data=request.data, partial=True)
    #     serializers.is_valid(raise_exception=True)


    #     return Response(
    #         {
    #             "message": "Payment updated successfully",
    #             "data": serializers.data
    #                      }, status=status.HTTP_200_OK)
class PaymentVerifyView(generics.GenericAPIView):
    serializer_class = PaymentVerifySerializer
    def post(self, request, *args, **kwargs):
        # get reference from TenantPayment model and verify payment with tenant id
        #how to get the tenant reference 
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reference = serializer.validated_data["reference"]

        # if not reference:
        #     return Response({"detail": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = TenantPayment.objects.get(reference=reference) # Fetch payment by reference
            if not payment:
                return Response({"detail": "Invalid reference"}, status=status.HTTP_404_NOT_FOUND)
            if payment.tenant != request.tenant:
                return Response({"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        except TenantPayment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        # Simulate payment verification logic
        if payment.status == "paid_verified":
            return Response({"detail": "Payment already verified"}, status=status.HTTP_200_OK)

        # Here you would integrate with the actual payment gateway to verify payment
        # For demonstration, we'll assume the payment is successful
        if not payment.plan:
            return Response({"detail": "Payment plan not associated with this payment"}, status=status.HTTP_400_BAD_REQUEST)
        payment.status = "paid_verified"                
        payment.paid_at = timezone.now()
        payment.expires_at = timezone.now().date() + timedelta(days=payment.plan.duration_days if payment.plan else None)  # e.g., 1 month subscription
        # payment.expires_at = timezone.now().date() + timedelta(minutes=5)  # e.g., 1 month subscription


        payment.save()

        # Update tenant's paid_until date
        tenant = payment.tenant
        tenant.paid_until = payment.expires_at
        tenant.grace_until = tenant.paid_until + timedelta(days=3)  # 3 days grace period
        tenant.on_trial = False
        tenant.save()

        return Response({"detail": "Payment verified successfully"}, status=status.HTTP_200_OK)

    


class PublicTenantBootstrapView(generics.ListCreateAPIView):
    serializer_class = PublicTenantBootstrapSerializer
    queryset = Tenant.objects.order_by('id')
    # pagination_class = Pagination

    # def get_queryset(self):
    #     return super().get_queryset().filter(schema_name='public')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Retry on IntegrityError to handle race conditions when creating public tenant
        attempts = 3
        for attempt in range(attempts):
            try:
                with transaction.atomic():
                    tenant = serializer.save()
                break
            except IntegrityError:
                if attempt < attempts - 1:
                    time.sleep(0.1)
                    continue
                return Response({
                    "detail": "Could not create public tenant due to a database integrity error."
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Public tenant created successfully",
            # "tenant": TenantSerializer(tenant).data,
            "tenant": PublicTenantBootstrapSerializer(tenant).data,
        }, status=status.HTTP_201_CREATED)


class ProvisionTenantView(generics.ListCreateAPIView):
    serializer_class = ProvisionTenantSerializer
    queryset = Tenant.objects.order_by('id')
    # pagination_class = Pagination

    def get_queryset(self):
        return super().get_queryset().exclude(schema_name='public')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attempts = 3
        for attempt in range(attempts):
            try:
                with transaction.atomic():
                    tenant = serializer.save()
                break
            except IntegrityError:
                if attempt < attempts - 1:
                    time.sleep(0.1)
                    continue
                return Response({
                    "detail": "Could not provision tenant due to a database integrity error."
                }, status=status.HTTP_400_BAD_REQUEST)
                
                
                
                if Tenant.objects.filter(schema_name=serializer.validated_data['schema_name']).exists(): 
                    return Response({ "detail": "A tenant with this schema name already exists."}, status=status.HTTP_400_BAD_REQUEST) 

        return Response({
            "message": "Tenant provisioned created successfully",
            # "tenant": TenantSerializer(tenant).data,
             "tenant": ProvisionTenantSerializer(tenant).data,
        }, status=status.HTTP_201_CREATED)

# class userListCreateView(generics.ListCreateAPIView):
#     queryset = UserAccount.objects.order_by('id')
#     serializer_class = userSerializer
# class TenantListCreateView(generics.ListCreateAPIView):
#     queryset = Tenant.objects.order_by('id')
#     serializer_class = TenantSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         tenant = serializer.save()
#         headers = self.get_success_headers(serializer.data)
#         return Response(
#             {
#                 "message": "Tenant created successfully",
#                 "tenant": TenantSerializer(tenant).data
#             },
#             status=status.HTTP_201_CREATED,
#             headers=headers
#         )





class AvailablePermissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantUser]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        with schema_context(tenant.schema_name):
            perms = Permission.objects.all().order_by('content_type__app_label', 'codename')
            data = [f"{p.content_type.app_label}.{p.codename}" for p in perms]

        return Response({'tenant_permissions': data})

class CurrentTenantPermissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantUser]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        if not tenant or not user:
            return Response({'detail': 'No tenant context or user'}, status=status.HTTP_400_BAD_REQUEST)

        with schema_context(tenant.schema_name):
            try:
                tenant_user = UserAccount.objects.get(pk=user.pk)
                groups = [g.name for g in tenant_user.usertenantpermissions.groups.all()]
                permissions = sorted(tenant_user.get_all_permissions())
            except Exception as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'tenant_groups': groups, 'tenant_permissions': permissions})

class TenantPermissionProtectedView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantUser, HasTenantPermission]
    permission_required = 'inventory.change_category'

    def get(self, request, *args, **kwargs):
        return Response({
            'detail': 'You have tenant permission to access this endpoint.',
            'tenant_groups': [g.name for g in request.user.usertenantpermissions.groups.all()],
            'tenant_permissions': sorted(request.user.get_all_permissions())
        })

class TenantGroupCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantOwnerOrAdmin]
    pagination_class = Pagination

    # to get group name and permissions list from request data, create group and assign permissions within tenant schema context
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Group.objects.none()
        with schema_context(tenant.schema_name):
            return Group.objects.all()
    

    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get('name')
        if not name:
            return Response({'name': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        perms = request.data.get('permissions', []) or []
        with schema_context(tenant.schema_name):
            group, created = Group.objects.get_or_create(name=name)
            if perms:
                # Clear existing permissions and set new ones
                group.permissions.clear()
                for perm_str in perms:
                    try:
                        app_label, codename = perm_str.split('.', 1)
                    except ValueError:
                        return Response({'permissions': 'Permission strings must be in format "app_label.codename"'}, status=status.HTTP_400_BAD_REQUEST)
                    perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
                    if not perm:
                        return Response({'permissions': f'Permission not found: {perm_str}'}, status=status.HTTP_400_BAD_REQUEST)
                    group.permissions.add(perm)
            group.save()
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(GroupSerializer(group).data, status=status_code)

class TenantGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer  
    permission_classes = [permissions.IsAuthenticated, IsTenantOwnerOrAdmin]  
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
    # permission_classes = [permissions.IsAuthenticated, IsTenantUser, HasModelPermissionForTenant]
    def get_object(self):
        tenant = getattr(self.request, 'tenant', None)
        group_id = self.kwargs.get('pk')
        if not tenant:
            raise Http404
        with schema_context(tenant.schema_name):
            group = Group.objects.filter(pk=group_id).first()
            if not group:
                raise Http404
            return group

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            "message": "Group updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)   

class TenantUserCreateView(generics.ListCreateAPIView):
    serializer_class = TenantUserCreateSerializer
    queryset = UserAccount.objects.order_by('id')
    permission_classes = [permissions.IsAuthenticated, IsTenantOwnerOrAdmin]
    pagination_class = Pagination
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        return UserAccount.objects.filter(tenants=tenant)
    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        # Ensure public/global user exists
        with schema_context(get_public_schema_name()):
            user = UserAccount.objects.filter(email=v['email']).first()
            if user:
                user.set_password(v['password'])
                if v.get('username'):
                    user.username = v.get('username')
                user.save()
            else:
                user = UserAccount.objects.create_user(email=v['email'], password=v['password'], username=v.get('username', ''))
                user.is_verified = True
                user.save()

        # add to tenant with roles
        try:
            tenant.add_user(user, is_superuser=v.get('is_superuser', False), is_staff=v.get('is_staff', False))
        except Exception as exc:
            return Response({'detail': f'Could not add user to tenant: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        

        groups = v.get('groups', []) or []
        if groups:
            with schema_context(tenant.schema_name):
                utp = user.usertenantpermissions
                for gname in groups:
                    grp, _ = Group.objects.get_or_create(name=gname)
                    utp.groups.add(grp)
                utp.save()

        return Response({'message': 'User created and added to tenant'}, status=status.HTTP_201_CREATED)


class TenantUserUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TenantUserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantOwnerOrAdmin]

    # lookup by public user id or pk; ensure the user belongs to this tenant
    def get_object(self):
        tenant = getattr(self.request, 'tenant', None)
        pk = self.kwargs.get('pk')
        user = UserAccount.objects.filter(pk=pk, tenants=tenant).first()
        if not user:
            raise Http404
        return user

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['tenant'] = getattr(self.request, 'tenant', None)
        return ctx

    def get_serializer_class(self):
        # Use the detailed serializer for GET (retrieve) so tenant groups/flags are returned,
        # but use the update serializer for PUT/PATCH.
        if self.request and self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return TenantUserDetailedSerializer
        return TenantUserUpdateSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            "message": "User updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    # def destroy(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     self.perform_destroy(instance)
    #     return Response({
    #         "message": "User removed from tenant successfully"
    #     }, status=status.HTTP_200_OK)
    
    def perform_destroy(self, instance):
        # Use the provided manager method to delete/unlink a user correctly
        # (UserProfile.delete() raises a DeleteError; use objects.delete_user)
        try:
            UserAccount.objects.delete_user(instance)
        except Exception:
            # Fallback to default delete if manager method unexpectedly fails
            # (pass force_drop to bypass UserProfile.delete guard)
            instance.delete(force_drop=True)

class UserPermissionsView(generics.GenericAPIView):
    
    
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        if not user or not user.is_authenticated:
            return Response({'detail': 'User not authenticated'}, status=401)
        tenant_user = UserAccount.objects.get(pk=user.pk)
        
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=400)
        
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            permissions = sorted(user.get_all_permissions())
            groups = [g.name for g in tenant_user.usertenantpermissions.groups.all()]
        
        return Response({
            'tenant_groups': groups,
            'tenant_permissions': permissions
        }) 
    


class AvailablePermissionsView(generics.GenericAPIView):
    """List all available permissions in the tenant that can be assigned to groups."""
    
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=400)
        
        with schema_context(tenant.schema_name):
            from django.contrib.auth.models import Permission
            
            # Get permissions from allowed apps
            allowed_apps = ['tenants', 'tenant_users', 'inventory', 'auth']
            permissions = Permission.objects.filter(
                content_type__app_label__in=allowed_apps
            ).order_by('content_type__app_label', 'codename')
            
            perm_list = []
            for p in permissions:
                perm_list.append({
                    'id': p.id,
                    'codename': f"{p.content_type.app_label}.{p.codename}",
                    'name': p.name,
                    'app': p.content_type.app_label
                })
            
            # Group by app
            grouped = {}
            for p in perm_list:
                app = p['app']
                if app not in grouped:
                    grouped[app] = []
                grouped[app].append(p)
            
            return Response({
                'all_permissions': perm_list,
                'grouped_by_app': grouped
            })
