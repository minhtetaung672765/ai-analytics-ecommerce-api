# analytics/urls.py
from django.urls import path
from .views import UploadCSVView, CustomerSegmentationView

urlpatterns = [
    path('upload/', UploadCSVView.as_view(), name='upload-csv'),
    path('segment-customers/', CustomerSegmentationView.as_view(), name='customer-segmentation'),
]
