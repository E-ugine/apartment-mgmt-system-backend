from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Case, When, BooleanField
from django.utils import timezone
from .models import Notice, NoticeReadStatus
from .serializers import (
    NoticeListSerializer, NoticeDetailSerializer, NoticeCreateSerializer,
    NoticeUpdateSerializer, ReadStatusSerializer, NoticeStatsSerializer,
    NoticeReadReportSerializer
)
from .permissions import NoticePermission

User = get_user_model()

class NoticeViewSet(viewsets.ModelViewSet):
    
    permission_classes = [NoticePermission]
    
    def get_queryset(self):
        """Filter notices based on user role"""
        user = self.request.user
        
        if user.is_tenant:
            # Tenants see notices targeted to them
            return Notice.objects.filter(
                Q(audience_type='all_tenants') |
                Q(audience_type='property', target_property__units__tenant=user) |
                Q(audience_type='unit', target_unit__tenant=user) |
                Q(audience_type='individual', target_user=user) |
                Q(audience_type='custom', custom_recipients=user),
                is_published=True
            ).filter(
                publish_date__lte=timezone.now()
            ).filter(
                Q(expiry_date__isnull=True) | Q(expiry_date__gt=timezone.now())
            ).distinct().select_related('created_by').prefetch_related('attachments')
        
        elif user.is_landlord:
            # Landlords see notices they created or for their properties
            return Notice.objects.filter(
                Q(created_by=user) |
                Q(audience_type='property', target_property__landlord=user) |
                Q(audience_type='unit', target_unit__property__landlord=user) |
                Q(audience_type='individual', target_user__assigned_unit__property__landlord=user)
            ).distinct().select_related('created_by').prefetch_related('attachments')
        
        elif user.is_caretaker:
            # Caretakers see notices they created or for properties they manage
            return Notice.objects.filter(
                Q(created_by=user) |
                Q(audience_type='property', target_property__caretakers=user) |
                Q(audience_type='unit', target_unit__property__caretakers=user)
            ).distinct().select_related('created_by').prefetch_related('attachments')
        
        return Notice.objects.none()
    
    def get_serializer_class(self):
        """Choose serializer based on action and user role"""
        if self.action == 'create':
            return NoticeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NoticeUpdateSerializer
        elif self.action == 'list':
            return NoticeListSerializer
        else:
            return NoticeDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to restrict to landlords and caretakers"""
        if request.user.is_tenant:
            return Response(
                {'error': 'Tenants cannot create notices'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to create read status when tenant views notice"""
        response = super().retrieve(request, *args, **kwargs)
        
        # If tenant is viewing the notice, create/update read status
        if request.user.is_tenant:
            notice = self.get_object()
            read_status, created = NoticeReadStatus.objects.get_or_create(
                notice=notice,
                user=request.user
            )
            # Don't automatically mark as read - let user do it explicitly
        
        return response
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notice as read for current user"""
        notice = self.get_object()
        
        # Only tenants can mark notices as read
        if not request.user.is_tenant:
            return Response(
                {'error': 'Only tenants can mark notices as read'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        read_status, created = NoticeReadStatus.objects.get_or_create(
            notice=notice,
            user=request.user
        )
        
        read_status.mark_as_read()
        
        return Response({
            'message': 'Notice marked as read',
            'read_at': read_status.read_at
        })
    
    @action(detail=False, methods=['get'])
    def my_feed(self, request):
        """
        Personalized notice feed for current user.
        Shows unread notices first, then read notices.
        """
        if not request.user.is_tenant:
            return Response(
                {'error': 'This endpoint is for tenants only'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get notices for this tenant
        queryset = self.get_queryset()
        
        # Annotate with read status
        queryset = queryset.annotate(
            is_read_status=Case(
                When(
                    read_statuses__user=request.user,
                    read_statuses__is_read=True,
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            )
        ).order_by('is_read_status', '-priority', '-publish_date')
        
        # Apply filters
        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        if unread_only:
            queryset = queryset.filter(is_read_status=False)
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NoticeListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = NoticeListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get notice statistics for current user.
        Different stats for different roles.
        """
        user = request.user
        
        if user.is_tenant:
            # Tenant stats: their notice summary
            notices = self.get_queryset()
            
            total_notices = notices.count()
            unread_notices = notices.exclude(
                read_statuses__user=user,
                read_statuses__is_read=True
            ).count()
            urgent_notices = notices.filter(priority='urgent').count()
            acknowledgment_pending = notices.filter(
                requires_acknowledgment=True
            ).exclude(
                read_statuses__user=user,
                read_statuses__is_read=True
            ).count()
            
            # Recent notices (last 5)
            recent_notices = notices.order_by('-publish_date')[:5]
            
            stats = {
                'total_notices': total_notices,
                'unread_notices': unread_notices,
                'urgent_notices': urgent_notices,
                'acknowledgment_pending': acknowledgment_pending,
                'recent_notices': recent_notices
            }
            
            serializer = NoticeStatsSerializer(stats, context={'request': request})
            return Response(serializer.data)
        
        elif user.role in ['landlord', 'caretaker']:
            # Creator stats: notices they've created
            created_notices = Notice.objects.filter(created_by=user)
            
            stats = {
                'total_created': created_notices.count(),
                'published': created_notices.filter(is_published=True).count(),
                'drafts': created_notices.filter(is_published=False).count(),
                'urgent': created_notices.filter(priority='urgent').count(),
                'requiring_acknowledgment': created_notices.filter(requires_acknowledgment=True).count()
            }
            
            return Response(stats)
        
        return Response({'error': 'Invalid user role'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def read_report(self, request, pk=None):
        """
        Get read status report for a specific notice.
        Available to notice creators only.
        """
        notice = self.get_object()
        
        # Only creators can view read reports
        if notice.created_by != request.user:
            return Response(
                {'error': 'Only notice creators can view read reports'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all intended recipients
        recipients = notice.get_recipients()
        total_recipients = recipients.count()
        
        # Get read statuses
        read_statuses = NoticeReadStatus.objects.filter(notice=notice)
        read_count = read_statuses.filter(is_read=True).count()
        unread_count = total_recipients - read_count
        
        read_percentage = (read_count / total_recipients * 100) if total_recipients > 0 else 0
        
        report = {
            'notice_id': notice.id,
            'notice_title': notice.title,
            'priority': notice.priority,
            'total_recipients': total_recipients,
            'read_count': read_count,
            'unread_count': unread_count,
            'read_percentage': round(read_percentage, 1),
            'requires_acknowledgment': notice.requires_acknowledgment,
            'publish_date': notice.publish_date
        }
        
        serializer = NoticeReadReportSerializer(report)
        return Response(serializer.data)