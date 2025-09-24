from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Property(models.Model):
    """
    Represents an apartment/building

    Model relationships:
    Property belongs to a Landlord(User)
    Property has many Units
    Property can have many Caretakers assigned
    """
    name = models.CharField(max_length=200, help_text="Name of the property(e.g Villa Rosa Gardens)")
    address = models.TextField(default='Not specified')
    description = models.TextField(blank=True, null=True, help_text="Additional text about the property")

    #Relationship: A property belongs to one Landlord
    landlord = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role':'landlord'}, #only landlords in dropdown
        related_name='properties' #landlord.properties.all()
        )
    
    caretakers = models.ManyToManyField(
        User,
        limit_choices_to={'role':'caretaker'},
        related_name='managed_properties', #caretaker.managed_properties.all()
        blank=True #Property cann exist without caretaker initially
    )

    total_units = models.PositiveIntegerField(
        default=0,
        help_text="Total number of units in this property"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Properties' #Plural form
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.landlord.username}"

    def update_total_units(self):
        """
        Update total units based on actual units count
        """
        self.total_units = self.units.count()
        self.save()

class Unit(models.Model):
    """
    Reps an infividual apartment unit within a property
    Model Relationship:
    Unit belongs to one Property
    Unit can be asigned to one Tenant
    """

    UNIT_STATUS_CHOICES = [
        ('available','Available'),
        ('occupied','Occupied'),
        ('maintenance','Under Maintenance'),
        ('reserved', 'Reserved'),
    ]

    #Unit belongs to one property
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='units' #property.units.all()
    )  

    unit_number = models.CharField(
        max_length=20,
        help_text="Unit identifier (e.g C20, Unit 5)"
    )    

    #Unit is assigned to one tenant
    tenant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # deleting tenant shouldn't delete unit
        limit_choices_to={'role':'tenant'},
        related_name='assigned_unit',
        null=True,
        blank=True
    )

    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=2, decimal_places=1, default=1.0)
    rent_amount = models.DecimalField(max_digits=10,decimal_places=2,help_text="Monthly rent amount")
    status = models.CharField(max_length=20, choices=UNIT_STATUS_CHOICES, default='available')
    description = models.TextField(blank=True, null=True, help_text="Additional unit description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        #ensures unit numbers are unique within a property
        unique_together = ['property','unit_number']    
        ordering = ['property','unit_number']

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"

    def save(self, *args, **kwargs):
        """Overide save to update status based on tenant assignment"""
        if self.tenant:
            self.status = 'occupied'
        elif self.status == 'occupied' and not self.tenant:
            self.status = 'available'

        super().save(*args, **kwargs)

        #update property's total_units count
        self.property.update_total_units()          
