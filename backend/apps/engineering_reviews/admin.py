from django.contrib import admin

from .models import EngineeringClarification, EngineeringFeasibilityReview

admin.site.register(EngineeringFeasibilityReview)
admin.site.register(EngineeringClarification)
