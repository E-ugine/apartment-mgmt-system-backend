from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notice, NoticeReadStatus, NoticeAttachment

User = get_user_model()

class NoticeAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for notice file attachments"""
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NoticeAttachment
        fields = ['id', 'filename', 'file_url', 'file_size', 'file_size_display', 'content_type']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size < 1024:
            return f"{obj.file_size} bytes"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"


class NoticeListSerializer(serializers.ModelSerializer):
    """
    Used in tenant/caretaker notice feeds.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_read = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    time_ago = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'priority', 'audience_type', 'requires_acknowledgment',
            'publish_date', 'expiry_date', 'is_active', 'created_by_name',
            'is_read', 'time_ago', 'attachment_count'
        ]
    
    def get_is_read(self, obj):
        """Check if current user has read this notice"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                read_status = obj.read_statuses.get(user=request.user)
                return read_status.is_read
            except NoticeReadStatus.DoesNotExist:
                return False
        return False
    
    def get_time_ago(self, obj):
        """Get human-readable time since publication"""
        now = timezone.now()
        diff = now - obj.publish_date
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    def get_attachment_count(self, obj):
        return obj.attachments.count()


class NoticeDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for notice viewing.
    Includes full message and attachments.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_read = serializers.SerializerMethodField()
    read_at = serializers.SerializerMethodField()
    attachments = NoticeAttachmentSerializer(many=True, read_only=True)
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'message', 'priority', 'audience_type',
            'requires_acknowledgment', 'publish_date', 'expiry_date',
            'created_by_name', 'is_read', 'read_at', 'attachments',
            'recipient_count', 'created_at', 'updated_at'
        ]
    
    def get_is_read(self, obj):
        """Check if current user has read this notice"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                read_status = obj.read_statuses.get(user=request.user)
                return read_status.is_read
            except NoticeReadStatus.DoesNotExist:
                return False
        return False
    
    def get_read_at(self, obj):
        """Get when current user read this notice"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                read_status = obj.read_statuses.get(user=request.user)
                return read_status.read_at
            except NoticeReadStatus.DoesNotExist:
                return None
        return None
    
    def get_recipient_count(self, obj):
        """Get count of intended recipients (for creators only)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Only show recipient count to creators, landlords, and caretakers
            if (request.user == obj.created_by or 
                request.user.role in ['landlord', 'caretaker']):
                return obj.get_recipient_count()
        return None


class NoticeCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notice
        fields = [
            'title', 'message', 'priority', 'audience_type',
            'target_property', 'target_unit', 'target_user', 'custom_recipients',
            'requires_acknowledgment', 'publish_date', 'expiry_date'
        ]
    
    def validate(self, attrs):
        """Custom validation for audience targeting"""
        audience_type = attrs.get('audience_type')
        
        # Validate required fields based on audience type
        if audience_type == 'property' and not attrs.get('target_property'):
            raise serializers.ValidationError({
                'target_property': 'This field is required when audience type is "property"'
            })
        
        if audience_type == 'unit' and not attrs.get('target_unit'):
            raise serializers.ValidationError({
                'target_unit': 'This field is required when audience type is "unit"'
            })
        
        if audience_type == 'individual' and not attrs.get('target_user'):
            raise serializers.ValidationError({
                'target_user': 'This field is required when audience type is "individual"'
            })
        
        if audience_type == 'custom' and not attrs.get('custom_recipients'):
            raise serializers.ValidationError({
                'custom_recipients': 'This field is required when audience type is "custom"'
            })
        
        # Validate expiry date is in the future
        expiry_date = attrs.get('expiry_date')
        if expiry_date and expiry_date <= timezone.now():
            raise serializers.ValidationError({
                'expiry_date': 'Expiry date must be in the future'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create notice with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class NoticeUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notice
        fields = [
            'title', 'message', 'priority', 'requires_acknowledgment',
            'is_published', 'expiry_date'
        ]
    
    def validate_expiry_date(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value


class ReadStatusSerializer(serializers.ModelSerializer):
    notice_title = serializers.CharField(source='notice.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = NoticeReadStatus
        fields = ['id', 'notice', 'notice_title', 'user_name', 'is_read', 'read_at']
        read_only_fields = ['read_at']


class NoticeStatsSerializer(serializers.Serializer):
    """
    Serializer for notice statistics.
    Used in dashboard endpoints.
    """
    total_notices = serializers.IntegerField()
    unread_notices = serializers.IntegerField()
    urgent_notices = serializers.IntegerField()
    acknowledgment_pending = serializers.IntegerField()
    recent_notices = NoticeListSerializer(many=True, read_only=True)


class NoticeReadReportSerializer(serializers.Serializer):
    """
    Serializer for read status reports.
    Used by landlords to track notice engagement.
    """
    notice_id = serializers.IntegerField()
    notice_title = serializers.CharField()
    priority = serializers.CharField()
    total_recipients = serializers.IntegerField()
    read_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_percentage = serializers.FloatField()
    requires_acknowledgment = serializers.BooleanField()
    publish_date = serializers.DateTimeField()