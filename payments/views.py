from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, datetime
from decimal import Decimal
from .models import Payment
from .serializers import (
    PaymentListSerializer, PaymentCreateSerializer, PaymentDetailSerializer,
    TenantPaymentSerializer, PaymentSummarySerializer, MonthlyReportSerializer
)
from .permissions import PaymentPermission

User = get_user_model()

class PaymentViewSet(viewsets.ModelViewSet):

    permission_classes = [PaymentPermission]
    
    def get_queryset(self):
        """Filter payments based on user role"""
        user = self.request.user
        
        if user.is_landlord:
            # Landlords see payments for their properties
            return Payment.objects.filter(
                unit__property__landlord=user
            ).select_related('tenant', 'unit', 'unit__property', 'recorded_by')
        
        elif user.is_caretaker:
            # Caretakers see payments for properties they manage
            return Payment.objects.filter(
                unit__property__caretakers=user
            ).select_related('tenant', 'unit', 'unit__property', 'recorded_by')
        
        elif user.is_tenant:
            # Tenants see only their own payments
            return Payment.objects.filter(
                tenant=user
            ).select_related('unit', 'unit__property')
        
        return Payment.objects.none()
    
    def get_serializer_class(self):
        user = self.request.user
        
        if user.is_tenant:
            return TenantPaymentSerializer

        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'list':
            return PaymentListSerializer
        else:
            return PaymentDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to add business logic"""
        # Only landlords and caretakers can create payments
        if request.user.is_tenant:
            return Response(
                {'error': 'Tenants cannot create payment records'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get payment summary for current month.
        Available to landlords and caretakers only.
        """
        if request.user.is_tenant:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        current_date = date.today()
        month = request.query_params.get('month', current_date.month)
        year = request.query_params.get('year', current_date.year)
        
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Invalid month or year'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get units user can access
        user = request.user
        if user.is_landlord:
            units = user.properties.all().prefetch_related('units__tenant')
        elif user.is_caretaker:
            units = user.managed_properties.all().prefetch_related('units__tenant')
        else:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        summary_data = []
        
        for property_obj in units:
            for unit in property_obj.units.all():
                if unit.tenant:  # Only include occupied units
                    balance_info = Payment.get_tenant_balance(unit.tenant, year, month)
                    
                    # Get last payment date
                    last_payment = Payment.objects.filter(
                        tenant=unit.tenant,
                        status='completed'
                    ).order_by('-date_paid').first()
                    
                    # Count payments this month
                    payment_count = Payment.objects.filter(
                        tenant=unit.tenant,
                        payment_year=year,
                        payment_month=month,
                        status='completed'
                    ).count()
                    
                    summary_data.append({
                        'unit': str(unit),
                        'unit_id': unit.id,
                        'tenant_name': unit.tenant.get_full_name(),
                        'expected_rent': balance_info['expected'],
                        'total_paid': balance_info['paid'],
                        'balance': balance_info['balance'],
                        'is_behind': balance_info['is_behind'],
                        'last_payment_date': last_payment.date_paid if last_payment else None,
                        'payment_count': payment_count
                    })
        
        serializer = PaymentSummarySerializer(summary_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """
        Generate monthly financial report.
        Available to landlords only.
        """
        if not request.user.is_landlord:
            return Response(
                {'error': 'Only landlords can access monthly reports'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range (default to last 6 months)
        current_date = date.today()
        months_back = int(request.query_params.get('months', 6))
        
        report_data = []
        
        for i in range(months_back):
            # Calculate month/year
            month_date = date(current_date.year, current_date.month, 1)
            if i > 0:
                # Go back i months
                if current_date.month - i > 0:
                    month_date = date(current_date.year, current_date.month - i, 1)
                else:
                    years_back = (i - current_date.month + 12) // 12
                    months_back_in_year = (i - current_date.month) % 12
                    month_date = date(current_date.year - years_back, 12 + months_back_in_year, 1)
            
            month = month_date.month
            year = month_date.year
            
            # Get all units in landlord's properties
            total_units = 0
            total_expected = Decimal('0.00')
            units_paid = 0
            units_behind = 0
            
            for property_obj in request.user.properties.all():
                for unit in property_obj.units.filter(tenant__isnull=False):
                    total_units += 1
                    total_expected += unit.rent_amount
                    
                    balance_info = Payment.get_tenant_balance(unit.tenant, year, month)
                    if balance_info['balance'] <= 0:
                        units_paid += 1
                    else:
                        units_behind += 1
            
            # Get total collected
            total_collected = Payment.objects.filter(
                unit__property__landlord=request.user,
                payment_year=year,
                payment_month=month,
                status='completed',
                payment_type='rent'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            report_data.append({
                'month': month,
                'year': year,
                'total_expected': total_expected,
                'total_collected': total_collected,
                'units_paid': units_paid,
                'units_behind': units_behind
            })
        
        # Reverse to show latest first
        report_data.reverse()
        
        serializer = MonthlyReportSerializer(report_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """
        Tenant-specific endpoint to view their payment history.
        """
        if not request.user.is_tenant:
            return Response(
                {'error': 'Only tenants can access this endpoint'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get payments with optional filtering
        queryset = self.get_queryset()
        
        # Filter by year if provided
        year = request.query_params.get('year')
        if year:
            try:
                queryset = queryset.filter(payment_year=int(year))
            except ValueError:
                pass
        
        # Filter by payment type if provided
        payment_type = request.query_params.get('type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        
        # Order by most recent first
        queryset = queryset.order_by('-date_paid', '-created_at')
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TenantPaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TenantPaymentSerializer(queryset, many=True)
        return Response(serializer.data)