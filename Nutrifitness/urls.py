from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('questionnaire-post', views.questionnaireData, name='questionnaire-post'),
    path('More-About-You', views.questionnaire, name='questionnaire'),
    path('', views.dashboard, name='dashboard'),
    path('pantry', views.myPantry, name='pantry'),
    path('api/', include('core.urls')),

    path('', include('django.contrib.auth.urls')),
]
