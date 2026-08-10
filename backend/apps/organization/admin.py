from django.contrib import admin

from .models import Branch, Company, Department, Designation, Employee, Warehouse

for model in (Company, Branch, Department, Designation, Warehouse, Employee):
    admin.site.register(model)
