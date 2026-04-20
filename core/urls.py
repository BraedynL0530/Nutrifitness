from django.urls import path
from . import views


urlpatterns = [
    path('upload-barcode/', views.uploadBarcode, name='upload-barcode'),
    path('food-search/', views.searchFood, name='food-search'),
    path('food-log/', views.saveFood, name='food-log'),
    path('food-log/<int:log_id>/', views.deleteFoodLog, name='delete-food-log'),
    path('food-log/bulk-delete/', views.bulkDeleteFoodLog, name='bulk-delete-food-log'),
    path('pantry-log/', views.saveItem, name='pantry-log'),
    path('pantry-item/<int:item_id>/', views.deletePantryItem, name='delete-pantry-item'),
    path('pantry-ai/', views.aiRecipe, name='pantry-ai'),
    #path('ml-res/',views.habitToWeight, name='ml-res'),
    path('weight-log/', views.saveWeight, name='weight-log'),
    path('streak-restore/', views.restoreStreak, name='streak-restore'),
    path('grocery-list/', views.generateGroceryList, name='grocery-list'),
]