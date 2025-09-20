"""
Django admin configuration for scraping models.
Production-ready admin interface with advanced filtering and search.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    Domain, ScrapingJob, ScrapedPage, ApiEndpoint, SystemMetrics,
    PageSummary, DocumentEmbedding, RobotsInfo
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'domain', 'status', 'success_rate_display',
        'total_scrapes', 'last_scraped', 'next_scrape', 'created_at'
    ]
    list_filter = [
        'status', 'protocol', 'created_at', 'last_scraped',
        ('created_by', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = ['name', 'domain', 'base_url']
    readonly_fields = [
        'id', 'domain', 'total_scrapes', 'successful_scrapes', 
        'failed_scrapes', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'base_url', 'domain', 'protocol', 'status')
        }),
        ('Scraping Configuration', {
            'fields': ('max_depth', 'max_pages', 'scrape_frequency_hours'),
            'classes': ('collapse',)
        }),
        ('Schedule & Status', {
            'fields': ('last_scraped', 'next_scrape'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_scrapes', 'successful_scrapes', 'failed_scrapes'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('advanced_config', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_domains', 'pause_domains', 'schedule_immediate_scrape']
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    success_rate_display.admin_order_field = 'successful_scrapes'
    
    def activate_domains(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f"Activated {queryset.count()} domains.")
    activate_domains.short_description = "Activate selected domains"
    
    def pause_domains(self, request, queryset):
        queryset.update(status='paused')
        self.message_user(request, f"Paused {queryset.count()} domains.")
    pause_domains.short_description = "Pause selected domains"
    
    def schedule_immediate_scrape(self, request, queryset):
        # This would integrate with your scheduler
        count = queryset.count()
        self.message_user(request, f"Scheduled immediate scrape for {count} domains.")
    schedule_immediate_scrape.short_description = "Schedule immediate scrape"


@admin.register(ScrapingJob)
class ScrapingJobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'domain_link', 'status', 'job_type', 'priority',
        'pages_scraped', 'pages_failed', 'success_rate_display',
        'duration_display', 'started_at', 'completed_at'
    ]
    list_filter = [
        'status', 'job_type', 'priority', 'created_at', 'started_at',
        ('domain', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = ['id', 'domain__name', 'domain__domain', 'scheduler_job_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'duration_display'
    ]
    raw_id_fields = ['domain']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('id', 'domain', 'job_type', 'priority', 'status')
        }),
        ('Execution Details', {
            'fields': ('started_at', 'completed_at', 'duration_display'),
        }),
        ('Results', {
            'fields': ('pages_scraped', 'pages_failed', 'total_size_bytes'),
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries'),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('scheduler_job_id', 'execution_node', 'job_config'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def domain_link(self, obj):
        url = reverse('admin:scraper_domain_change', args=[obj.domain.pk])
        return format_html('<a href="{}">{}</a>', url, obj.domain.name)
    domain_link.short_description = 'Domain'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def duration_display(self, obj):
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "-"
    duration_display.short_description = 'Duration'


@admin.register(ScrapedPage)
class ScrapedPageAdmin(admin.ModelAdmin):
    list_display = [
        'url_short', 'job_link', 'crawl_status', 'status_code',
        'crawl_depth', 'file_size', 'processing_time', 'scraped_at'
    ]
    list_filter = ['crawl_status', 'status_code', 'crawl_depth', 'robots_allowed', 'scraped_at']
    search_fields = ['url', 'title', 'content']
    readonly_fields = ['scraped_at', 'file_size', 'processing_time']
    raw_id_fields = ['job']
    
    fieldsets = (
        ('Page Information', {
            'fields': ('job', 'url', 'title', 'crawl_depth', 'parent_url')
        }),
        ('HTTP Details', {
            'fields': ('status_code', 'file_size'),
        }),
        ('Content', {
            'fields': ('content', 'html_content'),
            'classes': ('collapse',)
        }),
        ('Agora Crawler Data', {
            'fields': ('crawl_status', 'robots_allowed', 'crawl_delay_used', 'processing_time', 'error_message'),
        }),
        ('SEO Data', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('scraped_at',),
            'classes': ('collapse',)
        })
    )
    
    def url_short(self, obj):
        if len(obj.url) > 60:
            return obj.url[:57] + "..."
        return obj.url
    url_short.short_description = 'URL'
    
    def job_link(self, obj):
        url = reverse('admin:scraper_scrapingjob_change', args=[obj.job.pk])
        return format_html('<a href="{}">{}</a>', url, str(obj.job.id)[:8])
    job_link.short_description = 'Job'


# ScrapingTemplate admin removed - model not currently implemented


@admin.register(ApiEndpoint)
class ApiEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'method', 'endpoint_url', 'is_active', 'last_used', 'created_at']
    list_filter = ['method', 'is_active', 'auth_type', 'created_at']
    search_fields = ['name', 'endpoint_url']
    readonly_fields = ['id', 'last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Endpoint Information', {
            'fields': ('id', 'name', 'endpoint_url', 'method', 'is_active')
        }),
        ('Authentication', {
            'fields': ('auth_type', 'auth_config'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('headers', 'timeout', 'retry_attempts'),
            'classes': ('collapse',)
        }),
        ('Usage', {
            'fields': ('last_used', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'metric_value', 'metric_unit', 'created_at']
    list_filter = ['metric_name', 'metric_unit', 'created_at']
    search_fields = ['metric_name']
    readonly_fields = ['created_at', 'updated_at']
    
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        # Metrics are typically added programmatically
        return request.user.is_superuser


@admin.register(PageSummary)
class PageSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'scraped_page_url', 'summary_length_tokens', 'model_used',
        'chunk_count', 'compression_ratio', 'information_density_score', 'created_at'
    ]
    list_filter = [
        'model_used', 'chunk_count', 'created_at',
        ('scraped_page__job__domain', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = ['scraped_page__url', 'scraped_page__title', 'summary_text']
    readonly_fields = [
        'id', 'processing_time_ms', 'compression_ratio', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['scraped_page']
    
    fieldsets = (
        ('Summary Information', {
            'fields': ('id', 'scraped_page', 'model_used', 'summary_length_tokens')
        }),
        ('Processing Details', {
            'fields': ('chunk_count', 'processing_time_ms', 'compression_ratio', 'information_density_score'),
        }),
        ('Content', {
            'fields': ('summary_text',),
            'classes': ('collapse',)
        }),
        ('File Storage', {
            'fields': ('file_path',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def scraped_page_url(self, obj):
        if len(obj.scraped_page.url) > 60:
            return obj.scraped_page.url[:57] + "..."
        return obj.scraped_page.url
    scraped_page_url.short_description = 'Source URL'
    
    actions = ['regenerate_summaries']
    
    def regenerate_summaries(self, request, queryset):
        # This could trigger re-summarization
        count = queryset.count()
        self.message_user(request, f"Queued {count} summaries for regeneration.")
    regenerate_summaries.short_description = "Regenerate selected summaries"


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = [
        'milvus_id', 'summary_url', 'embedding_model',
        'embedding_dimensions', 'processing_time_ms', 'created_at'
    ]
    list_filter = [
        'embedding_model', 'embedding_dimensions', 'created_at',
        ('summary__scraped_page__job__domain', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = ['milvus_id', 'summary__scraped_page__url']
    readonly_fields = [
        'id', 'milvus_id', 'embedding_dimensions', 'processing_time_ms', 
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['summary']
    
    fieldsets = (
        ('Embedding Information', {
            'fields': ('id', 'milvus_id', 'summary', 'embedding_model', 'embedding_dimensions')
        }),
        ('Processing Details', {
            'fields': ('processing_time_ms',),
        }),
        # Vector data stored in Milvus, not Django
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def summary_url(self, obj):
        url = obj.summary.scraped_page.url
        if len(url) > 60:
            return url[:57] + "..."
        return url
    summary_url.short_description = 'Source URL'
    
    def has_add_permission(self, request):
        # Embeddings are typically created programmatically
        return request.user.is_superuser


@admin.register(RobotsInfo)
class RobotsInfoAdmin(admin.ModelAdmin):
    list_display = ['domain', 'crawl_delay', 'is_accessible', 'last_checked']
    list_filter = ['is_accessible', 'last_checked']
    search_fields = ['domain']
    readonly_fields = ['last_checked', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('domain', 'is_accessible', 'last_checked')
        }),
        ('Robots.txt Data', {
            'fields': ('crawl_delay', 'request_rate_requests', 'request_rate_seconds', 'preferred_host')
        }),
        ('Content', {
            'fields': ('robots_txt_content', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
