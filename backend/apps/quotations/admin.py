from django.contrib import admin

from .models import (
    CustomerCommercialConfirmation,
    Quotation,
    QuotationCommunication,
    QuotationGeneratedDocument,
    QuotationLine,
    QuotationNegotiation,
    QuotationRevision,
    QuotationTemplate,
    QuotationTextTemplate,
)

for model in (
    Quotation,
    QuotationRevision,
    QuotationLine,
    QuotationTemplate,
    QuotationTextTemplate,
    QuotationGeneratedDocument,
    QuotationCommunication,
    QuotationNegotiation,
    CustomerCommercialConfirmation,
):
    admin.site.register(model)
