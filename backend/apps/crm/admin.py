from django.contrib import admin

from .models import Customer, CustomerContact, CustomerSite

admin.site.register(Customer)
admin.site.register(CustomerContact)
admin.site.register(CustomerSite)
