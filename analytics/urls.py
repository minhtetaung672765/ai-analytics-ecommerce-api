# analytics/urls.py
from django.urls import path
from .views import (
    # AI analytics views
    UploadCSVView, 
    ExternalCustomerSegmentationView, 
    CustomerSegmentationView,
    TopProductsView,
    DiscountUsageAnalysisView,
    PurchaseCategoryPreferencesView,
    # other views...
    BasicAnalyticsOverview,
    CustomerListView,
    ProductListView,
    PurchaseListView,
    PurchaseItemListView
)

urlpatterns = [
    path('upload/', UploadCSVView.as_view(), name='upload-csv'),
    path('segment-customers-external/', ExternalCustomerSegmentationView.as_view(), name='external-customer-segmentation'),
    path('segment-customers/', CustomerSegmentationView.as_view(), name='customer-segmentation'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('discount-usage/', DiscountUsageAnalysisView.as_view(), name='discount-usage-analysis'),
    path('category-preferences/', PurchaseCategoryPreferencesView.as_view(), name='category-preferences'),

]

# endpoints for direct tables' data for frontend
urlpatterns += [
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('purchases/', PurchaseListView.as_view(), name='purchase-list'),
    path('purchase-items/', PurchaseItemListView.as_view(), name='purchase-item-list'),
    path('basic-analytics/', BasicAnalyticsOverview.as_view(), name='basic-analytics'),
]
