"""
URL patterns for the scraper API endpoints.
Provides RESTful API interface for external integrations.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

from .api_views import (
    DomainViewSet, ScrapingJobViewSet, ScrapedPageViewSet,
    ScrapingTemplateViewSet, SystemStatsAPIView, BulkScrapingAPIView
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'domains', DomainViewSet, basename='domain')
router.register(r'jobs', ScrapingJobViewSet, basename='job')
router.register(r'pages', ScrapedPageViewSet, basename='page')
router.register(r'templates', ScrapingTemplateViewSet, basename='template')

# URL patterns
urlpatterns = [
    # API root and viewsets
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('stats/', SystemStatsAPIView.as_view(), name='system_stats'),
    path('bulk-scrape/', BulkScrapingAPIView.as_view(), name='bulk_scrape'),
    
    # API documentation (temporarily disabled)
    # path('docs/', include_docs_urls(title='Scraping Platform API')),
]

# Add schema and browsable API patterns
from django.conf import settings
if settings.DEBUG:
    from rest_framework.schemas import get_schema_view
    
    urlpatterns += [
        path('schema/', get_schema_view(
            title="Scraping Platform API",
            description="Enterprise-grade web scraping platform API",
            version="1.0.0"
        ), name='openapi-schema'),
    ]
