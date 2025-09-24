from rest_framework import permissions

class PropertyPermission(permissions.BasePermission):
    """
    Custom permission for Property model
    Rules:
    - Landlords: Can perform CRUD on their own properties
    - Caretakers: Can view/update properties they manage
    - Tenants/Agents: No direct access to properties
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        #Only landlords and caretakers can access properties
        return request.user.role in ['landlord','caretaker']
    
    def has_object_permission(self, request, view, obj):
        user = request.user

        #landlords can access their own properties
        if user.is_landlord:
            return obj.landlord == user
        
        #caretakers can access properties they manage
        if user.is_caretaker:
            return user in obj.caretakers.all()
        
        return False

class UnitPermission(permissions.BasePermission):
    """
    custom permissions for Unit model
    Rules:
    - Landlords: Can perform CRUD to units in their properties
    - Caretakers: can perform CRUD to units they manage
    - Tenants: Can view their assigned unit only
    - Agent: No direct unit access
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        #All roles except agents can access units(controlled access though)
        return request.user.role in ['landlord','caretaker','tenant']

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_landlord:
            return obj.property.landlord == user

        if user.is_caretaker:
            return user in obj.property.caretakers.all()
        
        if user.is_tenant: #tenants can only view their assigned units
            if request.method in permissions.SAFE_METHODS:
                return obj.tenant == user  
            return False #tenants can't modify units
        return False  