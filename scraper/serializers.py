"""
Django REST Framework serializers for the scraping platform.
Professional API serialization with comprehensive data validation.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Domain, ScrapingJob, ScrapedPage, ScrapingTemplate, ApiEndpoint, SystemMetrics
import json


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class DomainSerializer(serializers.ModelSerializer):
    """Comprehensive domain serializer with statistics."""
    
    created_by = UserSerializer(read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'base_url', 'domain', 'protocol', 'max_depth', 'max_pages',
            'scrape_frequency_hours', 'status', 'last_scraped', 'next_scrape',
            'advanced_config', 'created_by', 'total_scrapes', 'successful_scrapes',
            'failed_scrapes', 'success_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'domain', 'last_scraped', 'next_scrape', 'total_scrapes',
            'successful_scrapes', 'failed_scrapes', 'success_rate', 'created_at', 'updated_at'
        ]
    
    def validate_base_url(self, value):
        """Validate the base URL format."""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(value)
            if not parsed.netloc or not parsed.scheme:
                raise serializers.ValidationError("Invalid URL format")
            if parsed.scheme not in ['http', 'https']:
                raise serializers.ValidationError("Only HTTP and HTTPS protocols are supported")
            return value
        except Exception as e:
            raise serializers.ValidationError(f"Invalid URL: {str(e)}")
    
    def validate_advanced_config(self, value):
        """Validate advanced configuration JSON."""
        if not value:
            return {}
        
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format")
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Advanced configuration must be a JSON object")
        
        return value


class DomainCreateSerializer(serializers.ModelSerializer):
    """Simplified domain serializer for creation."""
    
    class Meta:
        model = Domain
        fields = [
            'name', 'base_url', 'protocol', 'max_depth', 'max_pages',
            'scrape_frequency_hours', 'status', 'advanced_config'
        ]
    
    def create(self, validated_data):
        """Create domain with current user as owner."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ScrapingJobSerializer(serializers.ModelSerializer):
    """Serializer for scraping jobs with domain information."""
    
    domain = DomainSerializer(read_only=True)
    duration = serializers.SerializerMethodField()
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = ScrapingJob
        fields = [
            'id', 'domain', 'job_type', 'priority', 'status', 'started_at', 'completed_at',
            'duration', 'pages_scraped', 'pages_failed', 'total_size_bytes', 'success_rate',
            'error_message', 'retry_count', 'max_retries', 'scheduler_job_id',
            'execution_node', 'job_config', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'domain', 'started_at', 'completed_at', 'duration', 'pages_scraped',
            'pages_failed', 'total_size_bytes', 'success_rate', 'error_message',
            'retry_count', 'scheduler_job_id', 'execution_node', 'created_at', 'updated_at'
        ]
    
    def get_duration(self, obj):
        """Calculate job duration in seconds."""
        if obj.duration:
            return int(obj.duration.total_seconds())
        return None


class ScrapedPageSerializer(serializers.ModelSerializer):
    """Serializer for scraped page data."""
    
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    
    class Meta:
        model = ScrapedPage
        fields = [
            'id', 'job_id', 'url', 'depth_level', 'title', 'content', 'status_code',
            'content_type', 'content_length', 'status', 'processing_time_ms',
            'error_message', 'extracted_data', 'links_found', 'internal_links',
            'external_links', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'job_id', 'created_at', 'updated_at']


class ScrapedPageSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for page summaries."""
    
    class Meta:
        model = ScrapedPage
        fields = [
            'id', 'url', 'title', 'status', 'status_code', 'content_length',
            'processing_time_ms', 'created_at'
        ]


class ScrapingTemplateSerializer(serializers.ModelSerializer):
    """Serializer for reusable scraping templates."""
    
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ScrapingTemplate
        fields = [
            'id', 'name', 'description', 'selectors', 'rules', 'created_by',
            'is_public', 'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    
    def validate_selectors(self, value):
        """Validate selectors JSON structure."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for selectors")
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Selectors must be a JSON object")
        
        return value
    
    def validate_rules(self, value):
        """Validate rules JSON structure."""
        if not value:
            return {}
            
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for rules")
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Rules must be a JSON object")
        
        return value


class ApiEndpointSerializer(serializers.ModelSerializer):
    """Serializer for API endpoint configurations."""
    
    class Meta:
        model = ApiEndpoint
        fields = [
            'id', 'name', 'endpoint_url', 'method', 'auth_type', 'auth_config',
            'headers', 'timeout', 'retry_attempts', 'is_active', 'last_used',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_used', 'created_at', 'updated_at']
        extra_kwargs = {
            'auth_config': {'write_only': True}  # Hide sensitive auth data
        }


class SystemMetricsSerializer(serializers.ModelSerializer):
    """Serializer for system performance metrics."""
    
    class Meta:
        model = SystemMetrics
        fields = [
            'id', 'metric_name', 'metric_value', 'metric_unit', 'context_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Specialized serializers for different use cases

class DomainStatsSerializer(serializers.ModelSerializer):
    """Serializer focused on domain statistics."""
    
    success_rate = serializers.ReadOnlyField()
    recent_jobs = serializers.SerializerMethodField()
    avg_pages_per_job = serializers.SerializerMethodField()
    
    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'domain', 'status', 'total_scrapes', 'successful_scrapes',
            'failed_scrapes', 'success_rate', 'last_scraped', 'recent_jobs',
            'avg_pages_per_job'
        ]
    
    def get_recent_jobs(self, obj):
        """Get count of recent jobs (last 7 days)."""
        from django.utils import timezone
        from datetime import timedelta
        
        week_ago = timezone.now() - timedelta(days=7)
        return obj.scraping_jobs.filter(created_at__gte=week_ago).count()
    
    def get_avg_pages_per_job(self, obj):
        """Calculate average pages per job."""
        from django.db.models import Avg
        
        avg = obj.scraping_jobs.aggregate(avg_pages=Avg('pages_scraped'))['avg_pages']
        return round(avg, 2) if avg else 0


class JobProgressSerializer(serializers.ModelSerializer):
    """Real-time job progress serializer."""
    
    progress_percentage = serializers.SerializerMethodField()
    estimated_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = ScrapingJob
        fields = [
            'id', 'status', 'pages_scraped', 'pages_failed', 'progress_percentage',
            'estimated_completion', 'started_at'
        ]
    
    def get_progress_percentage(self, obj):
        """Calculate rough progress percentage."""
        if obj.status == 'completed':
            return 100
        elif obj.status == 'failed' or obj.status == 'cancelled':
            return 0
        elif obj.status == 'running' and obj.pages_scraped > 0:
            # Rough estimate based on scraped pages vs max pages
            max_pages = obj.domain.max_pages
            return min(round((obj.pages_scraped / max_pages) * 100), 95)
        return 0
    
    def get_estimated_completion(self, obj):
        """Estimate completion time based on current progress."""
        if obj.status != 'running' or not obj.started_at:
            return None
        
        from django.utils import timezone
        
        elapsed = timezone.now() - obj.started_at
        if obj.pages_scraped > 0:
            pages_remaining = obj.domain.max_pages - obj.pages_scraped
            avg_time_per_page = elapsed.total_seconds() / obj.pages_scraped
            estimated_seconds = pages_remaining * avg_time_per_page
            estimated_completion = timezone.now() + timezone.timedelta(seconds=estimated_seconds)
            return estimated_completion.isoformat()
        
        return None


class BulkScrapingRequestSerializer(serializers.Serializer):
    """Serializer for bulk scraping requests."""
    
    urls = serializers.ListField(
        child=serializers.URLField(),
        min_length=1,
        max_length=100,
        help_text="List of URLs to scrape"
    )
    
    priority = serializers.ChoiceField(
        choices=ScrapingJob.PRIORITY_CHOICES,
        default='medium',
        help_text="Priority level for all jobs"
    )
    
    max_depth = serializers.IntegerField(
        min_value=1,
        max_value=10,
        default=3,
        help_text="Maximum depth to scrape"
    )
    
    max_pages = serializers.IntegerField(
        min_value=1,
        max_value=1000,
        default=100,
        help_text="Maximum pages per domain"
    )
    
    advanced_config = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Advanced configuration options"
    )
    
    def validate_urls(self, value):
        """Validate that all URLs are unique and valid."""
        seen_urls = set()
        for url in value:
            if url in seen_urls:
                raise serializers.ValidationError(f"Duplicate URL found: {url}")
            seen_urls.add(url)
        return value


class ScrapingResultsSerializer(serializers.Serializer):
    """Serializer for structured scraping results."""
    
    domain = serializers.CharField()
    base_url = serializers.URLField()
    job_id = serializers.UUIDField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False)
    status = serializers.CharField()
    
    pages = ScrapedPageSummarySerializer(many=True)
    
    summary = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Summary statistics for the scraping job"
    )
    
    error = serializers.CharField(required=False, allow_blank=True)
