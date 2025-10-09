from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    #Authenticatication endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
     path('auth/logout/', views.LogoutView.as_view(), name='logout'),
     path('auth/token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),

    #user profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
]