from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import calendar
from datetime import date
from .models import Payment

User = get_user_model()

class PaymentListSerializer(serializers.ModelSerializer):
    """
    Used by caretakers and landlords for overview.
    """
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    unit_display = serializers.CharField(source='unit.__str__', read_only=True)
    period_display = serializers.CharField(read_only=True)
    amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'tenant_name', 'unit_display', 'amount', 'amount_display',
            'payment_type', 'payment_method', 'status', 'period_display',
            'date_paid', 'reference'
        ]
    
    def get_amount_display(self, obj):
        return f"${obj.amount:,.2f}"


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new payments.
    Used by caretakers and landlords to record payments.
    """
    
    class Meta:
        model = Payment
        fields = [
            'tenant', 'unit', 'amount', 'payment_type', 'payment_method',
            'payment_month', 'payment_year', 'reference', 'notes'
        ]
    
    def validate(self, attrs):
        """Custom validation for payment creation"""
        tenant = attrs.get('tenant')
        unit = attrs.get('unit')
        payment_type = attrs.get('payment_type')
        payment_month = attrs.get('payment_month')
        payment_year = attrs.get('payment_year')
        
        # Validate tenant is assigned to the unit
        if unit and tenant:
            if unit.tenant != tenant:
                raise serializers.ValidationError(
                    "Selected tenant is not assigned to this unit"
                )
        
        # For rent payments, validate month/year are provided
        if payment_type == 'rent':
            if not payment_month or not payment_year:
                raise serializers.ValidationError(
                    "Month and year are required for rent payments"
                )
            
            # Validate month range
            if not (1 <= payment_month <= 12):
                raise serializers.ValidationError(
                    "Payment month must be between 1 and 12"
                )
            
            # Validate year is reasonable
            current_year = date.today().year
            if not (current_year - 1 <= payment_year <= current_year + 1):
                raise serializers.ValidationError(
                    f"Payment year must be between {current_year-1} and {current_year+1}"
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create payment with proper defaults"""
        # Set recorded_by to current user
        validated_data['recorded_by'] = self.context['request'].user
        
        # For manual payments, set status to completed
        if validated_data.get('payment_method') in ['cash', 'bank_transfer', 'check']:
            validated_data['status'] = 'completed'
            validated_data['date_paid'] = timezone.now()
        
        return super().create(validated_data)


class PaymentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for payment view/update.
    Includes all related information.
    """
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    tenant_phone = serializers.CharField(source='tenant.phone', read_only=True)
    unit_display = serializers.CharField(source='unit.__str__', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    period_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'tenant', 'tenant_name', 'tenant_phone', 'unit', 'unit_display',
            'property_name', 'amount', 'payment_type', 'payment_method', 'status',
            'payment_month', 'payment_year', 'period_display', 'reference',
            'external_reference', 'payment_gateway', 'recorded_by_name',
            'date_created', 'date_paid', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tenant_name', 'tenant_phone', 'unit_display', 'property_name',
            'recorded_by_name', 'period_display', 'date_created', 'date_paid',
            'created_at', 'updated_at'
        ]


class TenantPaymentSerializer(serializers.ModelSerializer):
    """
    serializer for tenants to view their payment history.
    Excludes internal tracking information.
    """
    unit_display = serializers.CharField(source='unit.__str__', read_only=True)
    period_display = serializers.CharField(read_only=True)
    amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'unit_display', 'amount', 'amount_display', 'payment_type',
            'payment_method', 'status', 'period_display', 'date_paid', 'reference'
        ]
    
    def get_amount_display(self, obj):
        return f"${obj.amount:,.2f}"


class PaymentSummarySerializer(serializers.Serializer):
    """
    Serializer for financial summary data.
    Not tied to a model - used for dashboard endpoints.
    """
    unit = serializers.CharField()
    unit_id = serializers.IntegerField()
    tenant_name = serializers.CharField()
    expected_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_behind = serializers.BooleanField()
    last_payment_date = serializers.DateTimeField(allow_null=True)
    payment_count = serializers.IntegerField()


class MonthlyReportSerializer(serializers.Serializer):
    """
    Serializer for monthly financial reports.
    Used by landlords for overview.
    """
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    month_name = serializers.SerializerMethodField()
    total_expected = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    collection_rate = serializers.SerializerMethodField()
    units_paid = serializers.IntegerField()
    units_behind = serializers.IntegerField()
    
    def get_month_name(self, obj):
        return calendar.month_name[obj['month']]
    
    def get_collection_rate(self, obj):
        if obj['total_expected'] > 0:
            rate = (obj['total_collected'] / obj['total_expected']) * 100
            return f"{rate:.1f}%"
        return "0%"