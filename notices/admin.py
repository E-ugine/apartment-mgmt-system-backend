from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Notice, NoticeReadStatus, NoticeAttachment

class NoticeAttachmentInline(admin.TabularInline):
    model = NoticeAttachment
    extra = 1
    readonly_fields = ['file_size', 'content_type']

class NoticeReadStatusInline(admin.TabularInline):
    model = NoticeReadStatus
    extra = 0
    readonly_fields = ['read_at', 'created_at']
    can_delete = False

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'priority_badge', 'audience_type', 'recipient_count', 
        'is_published', 'created_by', 'publish_date'
    ]
    
    list_filter = [
        'priority', 'audience_type', 'is_published', 'requires_acknowledgment',
        'publish_date', 'created_by'
    ]
    
    search_fields = ['title', 'message']
    
    autocomplete_fields = ['created_by', 'target_property', 'target_unit', 'target_user']
    
    filter_horizontal = ['custom_recipients']
    
    readonly_fields = ['get_recipient_count', 'created_at', 'updated_at']
    
    inlines = [NoticeAttachmentInline]
    
    fieldsets = (
        ('Notice Content', {
            'fields': ('title', 'message', 'priority', 'requires_acknowledgment')
        }),
        ('Audience Targeting', {
            'fields': (
                'audience_type', 'target_property', 'target_unit', 
                'target_user', 'custom_recipients', 'get_recipient_count'
            )
        }),
        ('Publishing', {
            'fields': ('is_published', 'publish_date', 'expiry_date', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def priority_badge(self, obj):
        colors = {
            'low': 'green',
            'normal': 'blue',
            'high': 'orange',
            'urgent': 'red'
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def recipient_count(self, obj):
        return obj.get_recipient_count()
    recipient_count.short_description = 'Recipients'
    
    def get_recipient_count(self, obj):
        if obj.pk:  # Only for existing objects
            return f"{obj.get_recipient_count()} users"
        return "Save to see recipient count"
    get_recipient_count.short_description = 'Recipient Count'

@admin.register(NoticeReadStatus)
class NoticeReadStatusAdmin(admin.ModelAdmin):
    list_display = ['notice', 'user', 'is_read', 'read_at', 'created_at']
    list_filter = ['is_read', 'read_at', 'notice__priority']
    search_fields = ['notice__title', 'user__username', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['notice', 'user']
    readonly_fields = ['created_at']

@admin.register(NoticeAttachment)
class NoticeAttachmentAdmin(admin.ModelAdmin):
    list_display = ['notice', 'filename', 'file_size_display', 'uploaded_at']
    list_filter = ['content_type', 'uploaded_at']
    search_fields = ['notice__title', 'filename']
    readonly_fields = ['file_size', 'content_type', 'uploaded_at']
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size < 1024:
            return f"{obj.file_size} bytes"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'File Size'