from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Notice(models.Model):
    """
    Represents announcements, notifications, or important communications.
    
    - Flexible audience targeting (all tenants, specific properties, individuals)
    - Read status tracking for important notices
    - Priority levels for urgent communications
    - Future integration ready (email, SMS, push notifications)
    """
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    AUDIENCE_TYPES = [
        ('all_tenants', 'All Tenants'),
        ('property', 'Specific Property'),
        ('unit', 'Specific Unit'),
        ('individual', 'Individual Tenant'),
        ('caretakers', 'All Caretakers'),
        ('custom', 'Custom Selection'),
    ]
    
    # Basic notice information
    title = models.CharField(
        max_length=200,
        help_text="Notice headline or subject"
    )
    
    message = models.TextField(help_text="Full notice content")
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Audience targeting
    audience_type = models.CharField(
        max_length=20,
        choices=AUDIENCE_TYPES,
        default='all_tenants'
    )
    
    target_property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If audience_type is 'property'"
    )
    
    target_unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If audience_type is 'unit'"
    )
    
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='targeted_notices',
        help_text="If audience_type is 'individual'"
    )
    
    # Custom recipients (many-to-many for complex targeting)
    custom_recipients = models.ManyToManyField(
        User,
        blank=True,
        related_name='custom_notices',
        help_text="If audience_type is 'custom'"
    )
    
    # Publishing and scheduling
    is_published = models.BooleanField(default=True)
    
    publish_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this notice should become visible"
    )
    
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this notice should stop being visible"
    )
    
    # Tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        limit_choices_to={'role__in': ['landlord', 'caretaker']},
        related_name='created_notices'
    )
    
    requires_acknowledgment = models.BooleanField(
        default=False,
        help_text="Whether recipients must mark this as read"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-publish_date']
        indexes = [
            models.Index(fields=['audience_type', 'is_published']),
            models.Index(fields=['publish_date', 'expiry_date']),
            models.Index(fields=['priority', '-publish_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    def is_active(self):
        """Check if notice is currently active"""
        now = timezone.now()
        
        if not self.is_published:
            return False
        
        if self.publish_date > now:
            return False
        
        if self.expiry_date and self.expiry_date < now:
            return False
        
        return True
    
    def get_recipients(self):
        """
        Get all users who should see this notice.
        """
        if self.audience_type == 'all_tenants':
            return User.objects.filter(role='tenant', is_active=True)
        
        elif self.audience_type == 'property':
            if self.target_property:
                return User.objects.filter(
                    role='tenant',
                    assigned_unit__property=self.target_property,
                    is_active=True
                )
        
        elif self.audience_type == 'unit':
            if self.target_unit and self.target_unit.tenant:
                return User.objects.filter(id=self.target_unit.tenant.id)
        
        elif self.audience_type == 'individual':
            if self.target_user:
                return User.objects.filter(id=self.target_user.id)
        
        elif self.audience_type == 'caretakers':
            return User.objects.filter(role='caretaker', is_active=True)
        
        elif self.audience_type == 'custom':
            return self.custom_recipients.filter(is_active=True)
        
        return User.objects.none()
    
    def get_recipient_count(self):
        """Get count of users who should see this notice"""
        return self.get_recipients().count()
    
    def save(self, *args, **kwargs):
        """Override save for validation"""
        # Validate audience targeting
        if self.audience_type == 'property' and not self.target_property:
            raise ValueError("target_property is required when audience_type is 'property'")
        
        if self.audience_type == 'unit' and not self.target_unit:
            raise ValueError("target_unit is required when audience_type is 'unit'")
        
        if self.audience_type == 'individual' and not self.target_user:
            raise ValueError("target_user is required when audience_type is 'individual'")
        
        super().save(*args, **kwargs)


class NoticeReadStatus(models.Model):
    """
    Tracks which users have read which notices.
    Especially important for notices that require acknowledgment.
    """
    
    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notice_read_statuses'
    )
    
    is_read = models.BooleanField(default=False)
    
    read_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['notice', 'user']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notice', 'is_read']),
        ]
    
    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"{self.user.username} - {self.notice.title} ({status})"
    
    def mark_as_read(self):
        """Mark notice as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NoticeAttachment(models.Model):
    """
    Optional: File attachments for notices.
    Could be PDF announcements, images, documents, etc.
    """
    
    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    file = models.FileField(
        upload_to='notice_attachments/%Y/%m/',
        help_text="Attached file (PDF, image, document)"
    )
    
    filename = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['filename']
    
    def __str__(self):
        return f"{self.notice.title} - {self.filename}"
    
    def save(self, *args, **kwargs):
        """Set filename and metadata from uploaded file"""
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)