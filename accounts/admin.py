from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """This is the custom admin for our user model.
    It extends Django's built-in UserAdmin with our custom fields.
    """

    #Fields to display in the user list
    list_display = ['username', 'email', 'role', 'is_verified', 'is_active', 'created_at']

    # Filters in the right sidebar
    list_filter = ['role', 'is_verified', 'is_active', 'created_at']
    
    # Fields to search
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Default ordering
    ordering = ['-created_at']

    #Fields to show when editing a user
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'is_verified')
        }),
    )
    
    # Fields to show when creating a user
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone')
        }),
    )

