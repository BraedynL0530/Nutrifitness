from django.urls import path
from . import views


urlpatterns = [
    path('upload-barcode/', views.uploadBarcode, name='upload-barcode'),
]