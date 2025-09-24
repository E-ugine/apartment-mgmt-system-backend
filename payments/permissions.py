from rest_framework import permissions

class PaymentPermission(permissions.BasePermission):
    """
    Custom permission for Payment operations.
    
    Rules:
    - Landlords: Can view/create payments for their properties
    - Caretakers: Can view/create payments for managed properties
    - Tenants: Can view their own payments only
    - Agents: No payment access
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Only landlords, caretakers, and tenants can access payments
        return request.user.role in ['landlord', 'caretaker', 'tenant']
    
    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_landlord:
            return obj.unit.property.landlord == user

        if user.is_caretaker:
            return user in obj.unit.property.caretakers.all()
        if user.is_tenant:
            if request.method in permissions.SAFE_METHODS: 
                return obj.tenant == user
            return False  # Tenants can't create/modify payments
        
        return False