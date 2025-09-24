from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Property, Unit
from .serializers import (
    PropertyListSerializer, PropertyDetailSerializer,
    UnitListSerializer, UnitDetailSerializer, TenantUnitSerializer
)
from .permissions import PropertyPermission, UnitPermission

User = get_user_model()

class PropertyViewSet(viewsets.ModelViewSet):  
    permission_classes = [PropertyPermission]
    
    def get_queryset(self):
        """
        Filter properties based on user role.
        This is crucial for data security!
        """
        user = self.request.user
        
        if user.is_landlord:
            # Landlords see their own properties
            return Property.objects.filter(landlord=user).prefetch_related('caretakers')
        
        elif user.is_caretaker:
            # Caretakers see properties they manage
            return Property.objects.filter(caretakers=user).prefetch_related('caretakers')
        
        # Default: empty queryset (tenants, agents shouldn't see properties directly)
        return Property.objects.none()
    
    def get_serializer_class(self):
        """
        Choose serializer based on action.
        List views use lightweight serializer, detail views use full serializer.
        """
        if self.action == 'list':
            return PropertyListSerializer
        return PropertyDetailSerializer
    
    def perform_create(self, serializer):
        """
        Customize object creation.
        Automatically set landlord to current user if they're a landlord.
        """
        if self.request.user.is_landlord:
            serializer.save(landlord=self.request.user)
        else:
            # This shouldn't happen due to permissions, but safety first
            serializer.save()


class UnitViewSet(viewsets.ModelViewSet):
    """ViewSet for Unit CRUD operations with role-based filtering"""
    
    permission_classes = [UnitPermission]
    
    def get_queryset(self):
        """Filter units based on user role and permissions"""
        user = self.request.user
        
        if user.is_landlord:
            # Landlords see units in their properties
            return Unit.objects.filter(
                property__landlord=user
            ).select_related('property', 'tenant')
        
        elif user.is_caretaker:
            # Caretakers see units in properties they manage
            return Unit.objects.filter(
                property__caretakers=user
            ).select_related('property', 'tenant')
        
        elif user.is_tenant:
            # Tenants see only their assigned unit
            return Unit.objects.filter(tenant=user).select_related('property')
        
        return Unit.objects.none()
    
    def get_serializer_class(self):
        """Choose serializer based on user role and action"""
        user = self.request.user
        
        # Tenants get limited serializer
        if user.is_tenant:
            return TenantUnitSerializer
        
        # Landlords and caretakers get full access
        if self.action == 'list':
            return UnitListSerializer
        return UnitDetailSerializer
    
    def perform_create(self, serializer):
        """Ensure unit is created in a property the user can manage"""
        user = self.request.user
        property_obj = serializer.validated_data['property']
        
        # Verify user has permission to create units in this property
        if user.is_landlord and property_obj.landlord != user:
            raise permissions.PermissionDenied("You can only create units in your own properties")
        
        if user.is_caretaker and user not in property_obj.caretakers.all():
            raise permissions.PermissionDenied("You can only create units in properties you manage")
        
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Custom endpoint to get available units"""
        queryset = self.get_queryset().filter(status='available')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_tenant(self, request, pk=None):
        """Custom endpoint to assign tenant to unit"""
        unit = self.get_object()
        tenant_id = request.data.get('tenant_id')
        
        if not tenant_id:
            return Response(
                {'error': 'tenant_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tenant = User.objects.get(id=tenant_id, role='tenant')
        except User.DoesNotExist:
            return Response(
                {'error': 'Tenant not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if tenant already has a unit
        if tenant.assigned_unit.exists():
            return Response(
                {'error': 'Tenant already assigned to another unit'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        unit.tenant = tenant
        unit.save()
        
        serializer = self.get_serializer(unit)
        return Response(serializer.data)