from django.urls import path
from . import views


urlpatterns = [
    path('upload-barcode/', views.uploadBarcode, name='upload-barcode'),
    path('food-log/', views.saveFood, name='food-log'),
    path('pantry-log/', views.saveItem, name='pantry-log'),
    path('pantry-ai/', views.aiRecipe, name='pantry-ai'),
    path('ml-res/',views.habitToWeight, name='ml-res'),
    path('weight-log/',views.saveWeight, name='weight-log')
]