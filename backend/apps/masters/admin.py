from django.contrib import admin

from .models import Currency, DeliveryTerm, PaymentTerm, TaxRate, UnitOfMeasure

for model in (Currency, UnitOfMeasure, TaxRate, PaymentTerm, DeliveryTerm):
    admin.site.register(model)
