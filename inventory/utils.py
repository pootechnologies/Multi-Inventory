from .models import OrderLog, Report
from decimal import Decimal

def create_log(user, action, model_name, object_id, details=None):
    Log.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details
    )


def create_order_log(user, action, model_name, object_id, customer_info, product_name, product_specification, product_bundle, quantity, price, changes_on_update):
    # print("Order Log Active")
    OrderLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        customer_info = customer_info,
        product_name = product_name,
        product_specification = product_specification,
        product_bundle = product_bundle,
        quantity = quantity,
        price = price,
        changes_on_update = changes_on_update
    )
    

def create_order_report(user, customer_name, customer_phone, customer_tin_number, order_date, order_id, item_receipt, unit,  product_name, product_specification, product_price, quantity, sub_total, vat, payment_status, total_amount,):
    # print("Order Report Active")
    # item_receipt, unit, sub_total, vat, payment_status, paid_amount, unpaid_amount, total_amount

    Report.objects.create(
        user = user,
        customer_name = customer_name,
        customer_phone = customer_phone,
        customer_tin_number = customer_tin_number,
        order_date = order_date,
        order_id = order_id,
        item_receipt = item_receipt,
        product_name = product_name,
        product_specification = product_specification,
        unit = unit,
        product_price = product_price,
        quantity = quantity,
        sub_total = sub_total,
        vat = vat,
        payment_status = payment_status,
        total_amount = total_amount
    )




def update_payment_status_on_new_expense_or_product(supplier, expense=None, new_products=None):
    updated = False

    if expense and new_products:
        if expense.payment_status == 'Paid':
            expense.payment_status = 'Pending'
            expense.save(update_fields=['payment_status'])
            updated = True

    if supplier.payment_status == 'Paid':
        supplier.payment_status = 'Pending'
        supplier.unpaid_amount = supplier.total_amount - supplier.paid_amount
        supplier.save(update_fields=['payment_status', 'unpaid_amount'])
        updated = True

    return updated

