from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notices', views.NoticeViewSet, basename='notices')

app_name = 'notices'

urlpatterns = [
    path('', include(router.urls)),
]