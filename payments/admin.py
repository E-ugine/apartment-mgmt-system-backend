from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, PaymentSummary

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'tenant', 'unit', 'amount_display', 'payment_type', 
        'status_badge', 'period_display', 'date_paid', 'recorded_by'
    ]
    
    list_filter = [
        'payment_type', 'payment_method', 'status', 
        'payment_year', 'payment_month', 'date_paid'
    ]
    
    search_fields = [
        'tenant__username', 'tenant__first_name', 'tenant__last_name',
        'unit__unit_number', 'unit__property__name', 'reference'
    ]
    
    autocomplete_fields = ['tenant', 'unit', 'recorded_by']
    
    readonly_fields = ['created_at', 'updated_at', 'date_created']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('tenant', 'unit', 'amount', 'payment_type', 'status')
        }),
        ('Period & Method', {
            'fields': ('payment_month', 'payment_year', 'payment_method', 'payment_gateway')
        }),
        ('References', {
            'fields': ('reference', 'external_reference', 'recorded_by')
        }),
        ('Dates', {
            'fields': ('date_created', 'date_paid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    def amount_display(self, obj):
        return f"${obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange', 
            'processing': 'blue',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'purple'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'tenant', 'unit', 'unit__property', 'recorded_by'
        )

@admin.register(PaymentSummary)
class PaymentSummaryAdmin(admin.ModelAdmin):
    list_display = ['unit', 'month_year', 'expected_rent', 'total_paid', 'balance', 'is_fully_paid']
    list_filter = ['year', 'month', 'is_fully_paid']
    search_fields = ['unit__unit_number', 'unit__property__name']
    
    def month_year(self, obj):
        import calendar
        return f"{calendar.month_name[obj.month]} {obj.year}"
    month_year.short_description = 'Period'