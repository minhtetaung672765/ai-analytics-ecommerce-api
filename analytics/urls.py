# analytics/urls.py
from django.urls import path
from .views import (
    UploadCSVView, 
    ExternalCustomerSegmentationView, 
    CustomerSegmentationView,
    TopProductsView,
    DiscountUsageAnalysisView,
    PurchaseCategoryPreferencesView
)

urlpatterns = [
    path('upload/', UploadCSVView.as_view(), name='upload-csv'),
    path('segment-customers-external/', ExternalCustomerSegmentationView.as_view(), name='external-customer-segmentation'),
    path('segment-customers/', CustomerSegmentationView.as_view(), name='customer-segmentation'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('discount-usage/', DiscountUsageAnalysisView.as_view(), name='discount-usage-analysis'),
    path('category-preferences/', PurchaseCategoryPreferencesView.as_view(), name='category-preferences'),

]
