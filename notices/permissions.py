from rest_framework import permissions

class NoticePermission(permissions.BasePermission):
    """
    Custom permission for Notice operations.
    
    Rules:
    - Landlords: Can CRUD all notices for their properties
    - Caretakers: Can CRUD notices for properties they manage
    - Tenants: Can view notices targeted to them (read-only)
    - Agents: No notice access
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # All authenticated users except agents can access notices
        return request.user.role in ['landlord', 'caretaker', 'tenant']
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Tenants can only read notices targeted to them
        if user.is_tenant:
            if request.method in permissions.SAFE_METHODS:
                # Check if tenant is in notice recipients
                return user in obj.get_recipients()
            return False
        
        if user.is_landlord:
            if obj.created_by == user:
                return True
            
            # Notice targeted at landlord's properties/tenants
            if obj.audience_type == 'property' and obj.target_property:
                return obj.target_property.landlord == user
            
            if obj.audience_type == 'unit' and obj.target_unit:
                return obj.target_unit.property.landlord == user
            
            if obj.audience_type == 'individual' and obj.target_user:
                # Check if target user is tenant in landlord's property
                tenant_unit = obj.target_user.assigned_unit.first()
                if tenant_unit:
                    return tenant_unit.property.landlord == user
            
            # All tenants notices by this landlord
            if obj.audience_type == 'all_tenants' and obj.created_by == user:
                return True
        
        # Caretakers can access notices for properties they manage
        if user.is_caretaker:
            # Notice created by this caretaker
            if obj.created_by == user:
                return True
            
            # Notice for property they manage
            if obj.audience_type == 'property' and obj.target_property:
                return user in obj.target_property.caretakers.all()
            
            if obj.audience_type == 'unit' and obj.target_unit:
                return user in obj.target_unit.property.caretakers.all()
        
        return False