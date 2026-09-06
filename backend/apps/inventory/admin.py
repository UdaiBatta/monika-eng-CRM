from django.contrib import admin

from .models import Product, ProductCategory, StockItem, StockLocation, StockMovement, Supplier

for model in (ProductCategory, Supplier, Product, StockLocation, StockItem, StockMovement):
    admin.site.register(model)
