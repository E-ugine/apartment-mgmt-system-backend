from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    #Authenticatication endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/token/refresh/',TokenRefreshView.as_view(), name='token_refresh'),

    #user profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
]