from django.contrib import admin

from .models import (
    CustomerPurchaseOrder,
    CustomerPurchaseOrderRevision,
    SalesOrder,
    SalesOrderLine,
    SalesOrderRevision,
)

for model in (
    CustomerPurchaseOrder,
    CustomerPurchaseOrderRevision,
    SalesOrder,
    SalesOrderRevision,
    SalesOrderLine,
):
    admin.site.register(model)
