from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('landlord','Landlord'),
        ('caretaker','Caretaker'),
        ('tenant','Tenant'),
        ('agent','Agent'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15,blank=True, null=True, help_text='contact phone number')
    is_verified = models.BooleanField(default=False, help_text="Whether the tenant has been verified by an agent")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_users'
        ordering = ['-created_at'] #ordering. Start by the most recent

    def __str__(self):
        return f"{self.username} ({self.get_role_display()} )" 

    @property
    def is_landlord(self):
        return self.role == 'landlord'

    @property
    def is_caretaker(self):
        return self.role == 'caretaker'

    @property
    def is_tenant(self):
        return self.role == 'tenant'

    @property
    def is_agent(self):
        return self.role == 'agent'   

