from django.contrib import admin

from .models import CommercialEstimate, EstimateCostLine

admin.site.register(CommercialEstimate)
admin.site.register(EstimateCostLine)
