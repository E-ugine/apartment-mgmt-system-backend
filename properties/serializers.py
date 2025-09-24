from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Property, Unit

User = get_user_model()

class PropertyListSerializer(serializers.ModelSerializer):
    landlord_name = serializers.CharField(source='landlord.get_full_name', read_only=True)
    caretaker_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = ['id', 'name', 'address', 'landlord_name', 
                 'total_units', 'caretaker_count', 'created_at']
    
    def get_caretaker_count(self, obj):
        return obj.caretakers.count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer with nested relationships.
    Used for retrieve/create/update operations.
    """
    landlord = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='landlord'),
        required=True
    )
    
    caretakers = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='caretaker'),
        many=True,
        required=False
    )

    units = serializers.SerializerMethodField()
    landlord_name = serializers.CharField(source='landlord.get_full_name', read_only=True)
    caretaker_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = ['id', 'name', 'address', 'description', 'landlord', 'landlord_name',
                 'caretakers', 'caretaker_names', 'total_units', 'units', 
                 'created_at', 'updated_at']
        read_only_fields = ['total_units', 'created_at', 'updated_at']
    
    def get_units(self, obj):
        """Get basic unit info for this property"""
        units = obj.units.all().select_related('tenant')
        return [{
            'id': unit.id,
            'unit_number': unit.unit_number,
            'status': unit.status,
            'rent_amount': str(unit.rent_amount),
            'tenant': unit.tenant.get_full_name() if unit.tenant else None
        } for unit in units]
    
    def get_caretaker_names(self, obj):
        return [caretaker.get_full_name() for caretaker in obj.caretakers.all()]


class UnitListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'property_name', 'unit_number', 'status', 
                 'rent_amount', 'tenant_name', 'bedrooms', 'bathrooms']


class UnitDetailSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    tenant = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='tenant'),
        required=False,
        allow_null=True
    )
    
    # Display names (read-only)
    property_name = serializers.CharField(source='property.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    landlord_name = serializers.CharField(source='property.landlord.get_full_name', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'property', 'property_name', 'landlord_name', 'unit_number', 
                 'tenant', 'tenant_name', 'bedrooms', 'bathrooms', 'rent_amount',
                 'status', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, attrs):
        """Custom validation for unit assignment"""
        property_obj = attrs.get('property')
        tenant = attrs.get('tenant')
        
        # If tenant is assigned, check they don't have another unit
        if tenant and tenant.assigned_unit.exists():
            # Allow updating the same unit
            if self.instance and tenant.assigned_unit.first() == self.instance:
                pass  # Same unit, allow update
            else:
                raise serializers.ValidationError(
                    "This tenant is already assigned to another unit"
                )
        
        return attrs


class TenantUnitSerializer(serializers.ModelSerializer):
    """
    Limited serializer for tenants to view their own unit.
    Excludes sensitive information like rent amount comparisons.
    """
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_address = serializers.CharField(source='property.address', read_only=True)
    landlord_name = serializers.CharField(source='property.landlord.get_full_name', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'property_name', 'property_address', 'unit_number',
                 'bedrooms', 'bathrooms', 'rent_amount', 'status', 
                 'description', 'landlord_name']