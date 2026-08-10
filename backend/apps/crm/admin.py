from django.contrib import admin

from .models import CrmActivity, Customer, CustomerContact, CustomerSite

admin.site.register(Customer)
admin.site.register(CustomerContact)
admin.site.register(CustomerSite)
admin.site.register(CrmActivity)
