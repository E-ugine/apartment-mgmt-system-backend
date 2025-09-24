from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router automatically generates URLs for ViewSets
router = DefaultRouter()
router.register(r'properties', views.PropertyViewSet, basename='properties')
router.register(r'units', views.UnitViewSet, basename='units')

app_name = 'properties'

urlpatterns = [
    path('', include(router.urls)),
]