"""
Data models for the scraping platform.
Enterprise-grade design with proper indexing, validation, and extensibility.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import json


class TimestampedModel(models.Model):
    """Abstract base class with timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Domain(TimestampedModel):
    """Domain configuration for scraping."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('disabled', 'Disabled'),
        ('error', 'Error'),
    ]
    
    PROTOCOL_CHOICES = [
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('both', 'Both HTTP/HTTPS'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Display name for the domain")
    base_url = models.URLField(
        max_length=500,
        validators=[URLValidator()],
        help_text="Base URL to start scraping from (e.g., https://example.com/api/)"
    )
    domain = models.CharField(
        max_length=255, 
        db_index=True,
        help_text="Domain name extracted from base_url"
    )
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        default='https'
    )
    
    # Scraping configuration
    max_depth = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Maximum number of subpath levels to scrape"
    )
    max_pages = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text="Maximum number of pages to scrape per session"
    )
    
    # Scheduling configuration
    scrape_frequency_hours = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(8760)],
        help_text="How often to scrape this domain (in hours)"
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    last_scraped = models.DateTimeField(null=True, blank=True)
    next_scrape = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Advanced configuration (JSON field for extensibility)
    advanced_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Advanced scraping configuration in JSON format"
    )
    
    # Ownership and permissions
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_domains'
    )
    
    # Statistics
    total_scrapes = models.PositiveIntegerField(default=0)
    successful_scrapes = models.PositiveIntegerField(default=0)
    failed_scrapes = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['next_scrape', 'status']),
            models.Index(fields=['created_by', 'status']),
        ]
        unique_together = ['base_url', 'created_by']
    
    def __str__(self):
        return f"{self.name} ({self.domain})"
    
    def clean(self):
        """Custom validation."""
        super().clean()
        
        # Extract domain from base_url
        if self.base_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.base_url)
                if not parsed.netloc:
                    raise ValidationError({'base_url': 'Invalid URL format'})
                self.domain = parsed.netloc.lower()
            except Exception as e:
                raise ValidationError({'base_url': f'Invalid URL: {str(e)}'})
        
        # Validate advanced_config is valid JSON
        if self.advanced_config:
            try:
                if isinstance(self.advanced_config, str):
                    json.loads(self.advanced_config)
            except json.JSONDecodeError:
                raise ValidationError({'advanced_config': 'Invalid JSON format'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_scrapes == 0:
            return 0
        return round((self.successful_scrapes / self.total_scrapes) * 100, 2)
    
    def get_next_scrape_time(self):
        """Calculate next scrape time based on frequency."""
        if self.last_scraped:
            from datetime import timedelta
            return self.last_scraped + timedelta(hours=self.scrape_frequency_hours)
        return timezone.now()


class ScrapingJob(TimestampedModel):
    """Individual scraping job execution record."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='scraping_jobs'
    )
    
    # Job configuration
    job_type = models.CharField(
        max_length=50,
        default='scheduled',
        help_text="Type of scraping job (scheduled, manual, api)"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    # Execution details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results and statistics
    pages_scraped = models.PositiveIntegerField(default=0)
    pages_failed = models.PositiveIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Execution context
    scheduler_job_id = models.CharField(max_length=255, blank=True, db_index=True)
    execution_node = models.CharField(max_length=100, blank=True)
    
    # Metadata and configuration
    job_config = models.JSONField(
        default=dict,
        help_text="Job-specific configuration overrides"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['status', 'started_at']),
            models.Index(fields=['scheduler_job_id']),
        ]
    
    def __str__(self):
        return f"Job {self.id} - {self.domain.name} ({self.status})"
    
    @property
    def duration(self):
        """Calculate job duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    @property
    def success_rate(self):
        """Calculate page scraping success rate."""
        total_pages = self.pages_scraped + self.pages_failed
        if total_pages == 0:
            return 0
        return round((self.pages_scraped / total_pages) * 100, 2)


class ScrapedPage(TimestampedModel):
    """Individual scraped page data."""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('duplicate', 'Duplicate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        ScrapingJob,
        on_delete=models.CASCADE,
        related_name='scraped_pages'
    )
    
    # Page identification
    url = models.URLField(max_length=2000, db_index=True)
    url_hash = models.CharField(max_length=64, db_index=True)  # For deduplication
    depth_level = models.PositiveIntegerField(default=0)
    
    # Page content
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True, help_text="Extracted text content")
    raw_html = models.TextField(blank=True, help_text="Raw HTML content")
    
    # Metadata
    status_code = models.PositiveIntegerField(null=True)
    content_type = models.CharField(max_length=100, blank=True)
    content_length = models.BigIntegerField(null=True)
    last_modified = models.DateTimeField(null=True, blank=True)
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success'
    )
    processing_time_ms = models.PositiveIntegerField(null=True)
    error_message = models.TextField(blank=True)
    
    # Extracted data (extensible structure)
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured data extracted from the page"
    )
    
    # Links and relationships
    links_found = models.PositiveIntegerField(default=0)
    internal_links = models.PositiveIntegerField(default=0)
    external_links = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['url_hash']),
            models.Index(fields=['status', 'created_at']),
        ]
        unique_together = ['job', 'url_hash']
    
    def __str__(self):
        return f"{self.url} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Generate URL hash for deduplication
        if self.url:
            import hashlib
            self.url_hash = hashlib.sha256(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)


class ScrapingTemplate(TimestampedModel):
    """Reusable scraping templates for different site types."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Template configuration
    selectors = models.JSONField(
        help_text="CSS/XPath selectors for extracting data"
    )
    rules = models.JSONField(
        default=dict,
        help_text="Scraping rules and patterns"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scraping_templates'
    )
    is_public = models.BooleanField(default=False)
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ApiEndpoint(TimestampedModel):
    """API endpoints for external integrations."""
    
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    endpoint_url = models.URLField(max_length=1000)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='POST')
    
    # Authentication
    auth_type = models.CharField(max_length=50, default='none')
    auth_config = models.JSONField(default=dict, blank=True)
    
    # Configuration
    headers = models.JSONField(default=dict, blank=True)
    timeout = models.PositiveIntegerField(default=30)
    retry_attempts = models.PositiveIntegerField(default=3)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.method} {self.endpoint_url})"


class SystemMetrics(TimestampedModel):
    """System performance and usage metrics."""
    
    metric_name = models.CharField(max_length=100, db_index=True)
    metric_value = models.FloatField()
    metric_unit = models.CharField(max_length=20, blank=True)
    
    # Context
    context_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['metric_name', 'created_at']),
        ]
    
class PageSummary(TimestampedModel):
    """Dense summaries of scraped pages for embedding and retrieval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scraped_page = models.OneToOneField(
        ScrapedPage,
        on_delete=models.CASCADE,
        related_name='summary'
    )

    # Summary content
    summary_text = models.TextField(
        help_text="Dense, information-rich summary optimized for embedding"
    )
    summary_length_tokens = models.PositiveIntegerField(
        help_text="Token count of the summary text"
    )

    # Processing metadata
    processing_time_ms = models.PositiveIntegerField(null=True)
    model_used = models.CharField(
        max_length=100,
        default='azure-openai-gpt-5',
        help_text="LLM model used for summarization"
    )
    chunk_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of text chunks processed for summarization"
    )

    # Quality metrics
    compression_ratio = models.FloatField(
        help_text="Ratio of original content length to summary length"
    )
    information_density_score = models.FloatField(
        default=0.0,
        help_text="Estimated information density score (0-1)"
    )

    # File storage
    file_path = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Path to stored summary file on disk"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['model_used']),
        ]

    def __str__(self):
        return f"Summary for {self.scraped_page.url} ({self.summary_length_tokens} tokens)"

    @property
    def domain(self):
        """Get domain from the associated scraped page."""
        return self.scraped_page.job.domain.domain

    @property
    def url_path(self):
        """Get URL path for file organization."""
        from urllib.parse import urlparse
        return urlparse(self.scraped_page.url).path


class DocumentEmbedding(TimestampedModel):
    """Vector embeddings for document summaries stored in Milvus."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    summary = models.ForeignKey(
        PageSummary,
        on_delete=models.CASCADE,
        related_name='embeddings'
    )

    # Embedding data
    embedding_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique identifier in Milvus database"
    )
    embedding_vector = models.JSONField(
        help_text="Vector embedding data (stored as JSON for Django compatibility)"
    )

    # Metadata
    model_used = models.CharField(
        max_length=100,
        default='text-embedding-large-3',
        help_text="Embedding model used"
    )
    vector_dimensions = models.PositiveIntegerField(
        default=3072,
        help_text="Dimensionality of the embedding vector"
    )

    # Processing info
    processing_time_ms = models.PositiveIntegerField(null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['embedding_id']),
            models.Index(fields=['model_used']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Embedding {self.embedding_id} for {self.summary.scraped_page.url}"
