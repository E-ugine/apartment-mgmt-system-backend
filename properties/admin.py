from django.contrib import admin
from .models import Property, Unit

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name','landlord','total_units','created_at']
    list_filter = ['landlord','created_at']
    search_fields = ['name','address']
    filter_horizontal = ['caretakers']
    readonly_fields = ['total_units', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information',{
            'fields': ('name','description','address','landlord')
        }),
        ('Management',{
            'fields':('caretakers','total_units')
        }),
        ('Timestamps',{
            'fields':('created_at','updated_at'),
            'classes': ('collapse',) #collapsible section
        })
    )

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'tenant', 'status', 'rent_amount', 'bedrooms']
    list_filter = ['property', 'status', 'bedrooms']
    search_fields = ['unit_number', 'property__name']
    autocomplete_fields = ['property', 'tenant']  # Searchable dropdowns
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('property', 'unit_number', 'description')
        }),
        ('Assignment', {
            'fields': ('tenant', 'status')
        }),
        ('Details', {
            'fields': ('bedrooms', 'bathrooms', 'rent_amount')
        })
    )

    def get_queryset(self, request):
        """Optimize queries by joining related models"""
        return super().get_queryset(request).select_related('property','tenant')

