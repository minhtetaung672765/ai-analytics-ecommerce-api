from django.contrib import admin

from .models import Customer, Product, Purchase, PurchaseItem

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Purchase)
admin.site.register(PurchaseItem)

