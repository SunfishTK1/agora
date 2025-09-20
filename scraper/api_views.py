"""
Django REST Framework API views for the scraping platform.
Enterprise-grade API with comprehensive endpoints for external integration.
"""

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.shortcuts import get_object_or_404
from datetime import timedelta
import logging

from .models import Domain, ScrapingJob, ScrapedPage, ScrapingTemplate, SystemMetrics
from .serializers import (
    DomainSerializer, DomainCreateSerializer, DomainStatsSerializer,
    ScrapingJobSerializer, JobProgressSerializer,
    ScrapedPageSerializer, ScrapedPageSummarySerializer,
    ScrapingTemplateSerializer, SystemMetricsSerializer,
    BulkScrapingRequestSerializer, ScrapingResultsSerializer
)
from scheduler.scheduler_service import get_scheduler

logger = logging.getLogger(__name__)


class DomainViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing domains.
    
    Provides CRUD operations and additional actions for domain management.
    """
    
    queryset = Domain.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'protocol']
    search_fields = ['name', 'domain', 'base_url']
    ordering_fields = ['name', 'created_at', 'last_scraped', 'success_rate']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DomainCreateSerializer
        elif self.action == 'stats':
            return DomainStatsSerializer
        return DomainSerializer
    
    def get_queryset(self):
        """Filter queryset by user permissions."""
        if self.request.user.is_superuser:
            return Domain.objects.all()
        return Domain.objects.filter(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a domain for scraping."""
        domain = self.get_object()
        domain.status = 'active'
        domain.save()
        
        try:
            scheduler = get_scheduler()
            scheduler.schedule_domain_scraping(domain)
            return Response({
                'status': 'success',
                'message': f'Domain "{domain.name}" activated and scheduled'
            })
        except Exception as e:
            logger.error(f"Failed to schedule domain {domain.id}: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Domain activated but scheduling failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a domain's scraping schedule."""
        domain = self.get_object()
        domain.status = 'paused'
        domain.save()
        
        scheduler = get_scheduler()
        scheduler.unschedule_domain_scraping(domain)
        
        return Response({
            'status': 'success',
            'message': f'Domain "{domain.name}" paused'
        })
    
    @action(detail=True, methods=['post'])
    def scrape_now(self, request, pk=None):
        """Trigger immediate scraping for a domain."""
        domain = self.get_object()
        
        if domain.status != 'active':
            return Response({
                'status': 'error',
                'message': 'Domain must be active to trigger scraping'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            scheduler = get_scheduler()
            job_id = scheduler.schedule_immediate_scraping(domain)
            return Response({
                'status': 'success',
                'message': f'Immediate scraping scheduled for "{domain.name}"',
                'scheduler_job_id': job_id
            })
        except Exception as e:
            logger.error(f"Failed to schedule immediate scraping for {domain.id}: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Failed to schedule scraping: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def jobs(self, request, pk=None):
        """Get scraping jobs for a specific domain."""
        domain = self.get_object()
        jobs = domain.scraping_jobs.order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(jobs)
        if page is not None:
            serializer = ScrapingJobSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ScrapingJobSerializer(jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get detailed statistics for a domain."""
        domain = self.get_object()
        serializer = self.get_serializer(domain)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple domains from a list of URLs."""
        serializer = BulkScrapingRequestSerializer(data=request.data)
        if serializer.is_valid():
            created_domains = []
            errors = []
            
            for url in serializer.validated_data['urls']:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain_name = parsed.netloc.replace('www.', '').title()
                    
                    domain_data = {
                        'name': f"{domain_name} Scraping",
                        'base_url': url,
                        'max_depth': serializer.validated_data['max_depth'],
                        'max_pages': serializer.validated_data['max_pages'],
                        'status': 'active',
                        'advanced_config': serializer.validated_data.get('advanced_config', {})
                    }
                    
                    domain_serializer = DomainCreateSerializer(
                        data=domain_data,
                        context={'request': request}
                    )
                    
                    if domain_serializer.is_valid():
                        domain = domain_serializer.save()
                        created_domains.append(DomainSerializer(domain).data)
                        
                        # Schedule if active
                        if domain.status == 'active':
                            try:
                                scheduler = get_scheduler()
                                scheduler.schedule_domain_scraping(domain)
                            except Exception as e:
                                logger.error(f"Failed to schedule domain {domain.id}: {str(e)}")
                    else:
                        errors.append({
                            'url': url,
                            'errors': domain_serializer.errors
                        })
                        
                except Exception as e:
                    errors.append({
                        'url': url,
                        'errors': {'general': [str(e)]}
                    })
            
            return Response({
                'created_domains': created_domains,
                'errors': errors,
                'summary': {
                    'total_requested': len(serializer.validated_data['urls']),
                    'successfully_created': len(created_domains),
                    'failed': len(errors)
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScrapingJobViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing scraping jobs.
    
    Provides read-only access to job information and progress tracking.
    """
    
    queryset = ScrapingJob.objects.select_related('domain').order_by('-created_at')
    serializer_class = ScrapingJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'job_type', 'priority']
    search_fields = ['domain__name', 'domain__domain']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'pages_scraped']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter jobs by user permissions."""
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(domain__created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get real-time progress information for a job."""
        job = self.get_object()
        serializer = JobProgressSerializer(job)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def pages(self, request, pk=None):
        """Get scraped pages for a specific job."""
        job = self.get_object()
        pages = job.scraped_pages.order_by('-created_at')
        
        # Filter by status if requested
        status_filter = request.query_params.get('status')
        if status_filter:
            pages = pages.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(pages)
        if page is not None:
            serializer = ScrapedPageSummarySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ScrapedPageSummarySerializer(pages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get comprehensive results for a completed job."""
        job = self.get_object()
        
        if job.status not in ['completed', 'failed']:
            return Response({
                'error': 'Job results are only available for completed or failed jobs'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Build results structure
        pages_data = ScrapedPageSummarySerializer(
            job.scraped_pages.all(),
            many=True
        ).data
        
        results = {
            'domain': job.domain.domain,
            'base_url': job.domain.base_url,
            'job_id': str(job.id),
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'status': 'success' if job.status == 'completed' else 'error',
            'pages': pages_data,
            'summary': {
                'total_pages': job.pages_scraped + job.pages_failed,
                'successful_pages': job.pages_scraped,
                'failed_pages': job.pages_failed,
                'total_size_bytes': job.total_size_bytes or 0,
                'processing_time_seconds': job.duration.total_seconds() if job.duration else 0
            }
        }
        
        if job.status == 'failed':
            results['error'] = job.error_message
        
        serializer = ScrapingResultsSerializer(results)
        return Response(serializer.data)


class ScrapedPageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing scraped page data.
    
    Provides access to individual page content and metadata.
    """
    
    queryset = ScrapedPage.objects.select_related('job', 'job__domain').order_by('-created_at')
    serializer_class = ScrapedPageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'status_code', 'depth_level']
    search_fields = ['url', 'title', 'content']
    ordering_fields = ['created_at', 'processing_time_ms', 'content_length']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter pages by user permissions."""
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(job__domain__created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Get full content for a specific page."""
        page = self.get_object()
        return Response({
            'url': page.url,
            'title': page.title,
            'content': page.content,
            'raw_html': page.raw_html,
            'extracted_data': page.extracted_data,
            'metadata': {
                'status_code': page.status_code,
                'content_type': page.content_type,
                'content_length': page.content_length,
                'processing_time_ms': page.processing_time_ms,
                'created_at': page.created_at
            }
        })


class ScrapingTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scraping templates.
    
    Allows users to create reusable scraping configurations.
    """
    
    queryset = ScrapingTemplate.objects.order_by('name')
    serializer_class = ScrapingTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'usage_count']
    ordering = ['name']
    
    def get_queryset(self):
        """Return public templates and user's private templates."""
        if self.request.user.is_superuser:
            return self.queryset
        
        return self.queryset.filter(
            Q(is_public=True) | Q(created_by=self.request.user)
        )
    
    def perform_create(self, serializer):
        """Set the current user as template creator."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """Increment usage count when template is used."""
        template = self.get_object()
        template.usage_count += 1
        template.save(update_fields=['usage_count'])
        
        return Response({
            'status': 'success',
            'message': f'Template "{template.name}" usage recorded'
        })


class SystemStatsAPIView(generics.GenericAPIView):
    """
    API view for system-wide statistics and health metrics.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive system statistics."""
        
        # Basic counts
        stats = {
            'domains': {
                'total': Domain.objects.count(),
                'active': Domain.objects.filter(status='active').count(),
                'paused': Domain.objects.filter(status='paused').count(),
                'error': Domain.objects.filter(status='error').count(),
            },
            'jobs': {
                'total': ScrapingJob.objects.count(),
                'running': ScrapingJob.objects.filter(status='running').count(),
                'completed': ScrapingJob.objects.filter(status='completed').count(),
                'failed': ScrapingJob.objects.filter(status='failed').count(),
            },
            'pages': {
                'total': ScrapedPage.objects.count(),
                'successful': ScrapedPage.objects.filter(status='success').count(),
                'failed': ScrapedPage.objects.filter(status='failed').count(),
            }
        }
        
        # Time-based statistics
        now = timezone.now()
        today = now.date()
        this_week = now - timedelta(days=7)
        this_month = now - timedelta(days=30)
        
        stats['activity'] = {
            'jobs_today': ScrapingJob.objects.filter(created_at__date=today).count(),
            'jobs_this_week': ScrapingJob.objects.filter(created_at__gte=this_week).count(),
            'jobs_this_month': ScrapingJob.objects.filter(created_at__gte=this_month).count(),
            'pages_today': ScrapedPage.objects.filter(created_at__date=today).count(),
            'pages_this_week': ScrapedPage.objects.filter(created_at__gte=this_week).count(),
            'pages_this_month': ScrapedPage.objects.filter(created_at__gte=this_month).count(),
        }
        
        # Performance metrics
        recent_jobs = ScrapingJob.objects.filter(
            status='completed',
            completed_at__gte=this_week
        )
        
        if recent_jobs.exists():
            avg_duration = recent_jobs.aggregate(
                avg_duration=Avg('completed_at__second') - Avg('started_at__second')
            )
            avg_pages = recent_jobs.aggregate(Avg('pages_scraped'))['pages_scraped__avg']
            
            stats['performance'] = {
                'avg_job_duration_seconds': avg_duration.get('avg_duration', 0),
                'avg_pages_per_job': round(avg_pages or 0, 2),
                'success_rate': round(
                    (recent_jobs.count() / ScrapingJob.objects.filter(created_at__gte=this_week).count()) * 100,
                    2
                ) if ScrapingJob.objects.filter(created_at__gte=this_week).exists() else 0
            }
        else:
            stats['performance'] = {
                'avg_job_duration_seconds': 0,
                'avg_pages_per_job': 0,
                'success_rate': 0
            }
        
        # Scheduler status
        scheduler = get_scheduler()
        stats['scheduler'] = scheduler.get_scheduler_status()
        
        # System metrics
        recent_metrics = SystemMetrics.objects.filter(
            created_at__gte=this_week
        ).values('metric_name').annotate(
            avg_value=Avg('metric_value'),
            count=Count('id')
        )
        
        stats['metrics'] = {
            metric['metric_name']: {
                'average': round(metric['avg_value'], 2),
                'count': metric['count']
            }
            for metric in recent_metrics
        }
        
        stats['timestamp'] = now.isoformat()
        
        return Response(stats)


class BulkScrapingAPIView(generics.CreateAPIView):
    """
    API view for submitting bulk scraping requests.
    """
    
    serializer_class = BulkScrapingRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Process bulk scraping request."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            
            # Create temporary domains for bulk scraping
            created_jobs = []
            errors = []
            scheduler = get_scheduler()
            
            for url in serializer.validated_data['urls']:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain_name = f"Bulk-{parsed.netloc}"
                    
                    # Create temporary domain
                    domain = Domain.objects.create(
                        name=domain_name,
                        base_url=url,
                        created_by=request.user,
                        max_depth=serializer.validated_data['max_depth'],
                        max_pages=serializer.validated_data['max_pages'],
                        status='active',
                        advanced_config=serializer.validated_data.get('advanced_config', {})
                    )
                    
                    # Schedule immediate scraping
                    job_id = scheduler.schedule_immediate_scraping(domain)
                    
                    created_jobs.append({
                        'url': url,
                        'domain_id': str(domain.id),
                        'scheduler_job_id': job_id,
                        'status': 'scheduled'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to create bulk job for {url}: {str(e)}")
                    errors.append({
                        'url': url,
                        'error': str(e)
                    })
            
            response_data = {
                'status': 'success',
                'created_jobs': created_jobs,
                'errors': errors,
                'summary': {
                    'total_requested': len(serializer.validated_data['urls']),
                    'successfully_scheduled': len(created_jobs),
                    'failed': len(errors)
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
