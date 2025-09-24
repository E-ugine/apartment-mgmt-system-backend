from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import calendar

User = get_user_model()

class Payment(models.Model):
    """
    Represents a payment transaction for rent, deposits, or services.
    - Auditable: Tracks who recorded what and when
    """
    
    PAYMENT_TYPES = [
        ('rent', 'Monthly Rent'),
        ('deposit', 'Security Deposit'),
        ('service', 'Service Charge'),
        ('late_fee', 'Late Fee'),
        ('maintenance', 'Maintenance Fee'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('check', 'Check'),
        ('stripe', 'Stripe'),  # future integration
        ('mpesa', 'M-Pesa'),   # future integration
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'), 
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'), 
        ('cancelled', 'Cancelled'), 
        ('refunded', 'Refunded'), 
    ]
    
    # Core payment information
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'tenant'},
        related_name='payments'
    )
    
    unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Payment amount"
    )
    
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='rent'
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash'
    )
    
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='completed'  # For manual payments, they're completed immediately
    )
    
    # Date tracking
    date_created = models.DateTimeField(auto_now_add=True)
    date_paid = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the payment was actually completed"
    )
    
    # Period tracking (for rent payments)
    payment_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Month this payment covers (1-12)"
    )
    payment_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Year this payment covers"
    )
    
    # Reference and tracking
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Receipt number, transaction ID, etc."
    )
    
    external_reference = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Payment gateway transaction ID (Stripe, M-Pesa, etc.)"
    )
    
    payment_gateway = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Which system processed this payment"
    )
    
    # Who recorded this payment
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Don't delete if user is deleted
        limit_choices_to={'role__in': ['landlord', 'caretaker']},
        related_name='recorded_payments',
        null=True,
        blank=True
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this payment"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_paid', '-date_created']
        indexes = [
            models.Index(fields=['tenant', '-date_paid']),
            models.Index(fields=['unit', '-date_paid']),
            models.Index(fields=['payment_year', 'payment_month']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        period = ""
        if self.payment_month and self.payment_year:
            month_name = calendar.month_name[self.payment_month]
            period = f" ({month_name} {self.payment_year})"
        
        return f"{self.tenant.username} - {self.get_payment_type_display()} - ${self.amount}{period}"
    
    def save(self, *args, **kwargs):
        """Override save to set date_paid for completed manual payments"""
        if self.status == 'completed' and not self.date_paid:
            self.date_paid = timezone.now()
        
        # Set payment gateway for manual payments
        if not self.payment_gateway:
            if self.payment_method in ['cash', 'bank_transfer', 'check']:
                self.payment_gateway = 'manual'
        
        super().save(*args, **kwargs)
    
    @property
    def is_rent_payment(self):
        return self.payment_type == 'rent'
    
    @property
    def period_display(self):
        """Display payment period in readable format"""
        if self.payment_month and self.payment_year:
            month_name = calendar.month_name[self.payment_month]
            return f"{month_name} {self.payment_year}"
        return "N/A"
    
    @classmethod
    def get_monthly_total(cls, unit, year, month):
        """Get total payments for a unit in a specific month"""
        return cls.objects.filter(
            unit=unit,
            payment_year=year,
            payment_month=month,
            status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @classmethod
    def get_tenant_balance(cls, tenant, year, month):
        """Calculate if tenant is up to date with rent"""
        unit = tenant.assigned_unit.first()
        if not unit:
            return {'unit': None, 'expected': 0, 'paid': 0, 'balance': 0}
        
        expected_rent = unit.rent_amount
        paid_amount = cls.get_monthly_total(unit, year, month)
        balance = expected_rent - paid_amount
        
        return {
            'unit': unit,
            'expected': expected_rent,
            'paid': paid_amount,
            'balance': balance,
            'is_behind': balance > 0
        }


class PaymentSummary(models.Model):
    """
    Optional: Monthly summary model for faster reporting.
    """
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    
    expected_rent = models.DecimalField(max_digits=10, decimal_places=2)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_count = models.PositiveIntegerField(default=0)
    
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_fully_paid = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['unit', 'year', 'month']
        ordering = ['-year', '-month', 'unit']
    
    def __str__(self):
        month_name = calendar.month_name[self.month]
        return f"{self.unit} - {month_name} {self.year} - Balance: ${self.balance}"