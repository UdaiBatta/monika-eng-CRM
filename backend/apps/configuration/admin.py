from django.contrib import admin

from .models import CompanySettings, FeatureFlag

admin.site.register(CompanySettings)
admin.site.register(FeatureFlag)
