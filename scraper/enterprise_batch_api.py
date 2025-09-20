"""
Enterprise Batch Processing API for $25M/Year Platform
World-class data engineering infrastructure for web scraping at scale
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from .models import Domain, ScrapingJob, ScrapedPage
from .services import ScrapingService
from .agora_crawler import get_agora_crawler_service

logger = logging.getLogger(__name__)


@dataclass
class EnterpriseScrapeRequest:
    """Standardized enterprise scrape request format."""
    domain: str
    starting_path: str = ""
    max_depth: int = 3
    max_pages: int = 100
    frequency_hours: int = 24
    include_subdomains: bool = False
    path_patterns: List[str] = None
    exclude_patterns: List[str] = None
    priority: str = "medium"
    callback_url: Optional[str] = None
    
    def __post_init__(self):
        if self.path_patterns is None:
            self.path_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


@dataclass 
class EnterpriseScrapeResponse:
    """Standardized enterprise response format - exactly what you requested."""
    starting_domain: str
    urls_scraped: List[Dict[str, Any]]
    webpage_contents: Dict[str, str]  # URL -> text content mapping
    job_id: str
    status: str
    total_pages: int
    successful_pages: int
    processing_time_seconds: float
    timestamp: str
    metadata: Dict[str, Any]


class EnterpriseBatchProcessor:
    """
    Enterprise-grade batch processing system.
    Handles large-scale domain scraping with advanced scheduling.
    """
    
    def __init__(self):
        self.scraping_service = ScrapingService(use_dummy_api=False)
        self.crawler_service = get_agora_crawler_service()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.active_jobs = {}
        
    async def process_batch_request(self, requests: List[EnterpriseScrapeRequest]) -> Dict[str, Any]:
        """Process multiple scraping requests in parallel."""
        logger.info(f"Processing batch of {len(requests)} scraping requests")
        
        batch_id = str(uuid.uuid4())
        start_time = timezone.now()
        
        # Process requests in parallel
        tasks = []
        for req in requests:
            task = asyncio.create_task(self._process_single_request(req, batch_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile batch results
        successful_jobs = []
        failed_jobs = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_jobs.append({
                    'domain': requests[i].domain,
                    'error': str(result)
                })
            else:
                successful_jobs.append(result)
        
        processing_time = (timezone.now() - start_time).total_seconds()
        
        return {
            'batch_id': batch_id,
            'status': 'completed',
            'total_requests': len(requests),
            'successful_jobs': len(successful_jobs),
            'failed_jobs': len(failed_jobs),
            'processing_time_seconds': processing_time,
            'results': successful_jobs,
            'errors': failed_jobs,
            'timestamp': timezone.now().isoformat()
        }
    
    async def _process_single_request(self, request: EnterpriseScrapeRequest, batch_id: str) -> EnterpriseScrapeResponse:
        """Process a single scraping request with enterprise features."""
        
        # Create or get domain
        domain, created = Domain.objects.get_or_create(
            base_url=f"https://{request.domain}{request.starting_path}",
            defaults={
                'name': f"Enterprise - {request.domain}",
                'domain': request.domain,
                'max_depth': request.max_depth,
                'max_pages': request.max_pages,
                'scrape_frequency_hours': request.frequency_hours,
                'status': 'active',
                'advanced_config': {
                    'include_subdomains': request.include_subdomains,
                    'path_patterns': request.path_patterns,
                    'exclude_patterns': request.exclude_patterns,
                    'batch_id': batch_id
                }
            }
        )
        
        # Create scraping job
        job = ScrapingJob.objects.create(
            domain=domain,
            job_type='batch_api',
            priority=request.priority,
            status='running',
            started_at=timezone.now(),
            job_config={
                'batch_id': batch_id,
                'starting_path': request.starting_path,
                'enterprise_request': asdict(request)
            }
        )
        
        start_time = timezone.now()
        
        try:
            # Perform recursive crawling
            crawl_data = self.crawler_service.crawl_recursive(
                start_url=f"https://{request.domain}{request.starting_path}",
                max_depth=request.max_depth,
                max_pages_per_level=request.max_pages
            )
            
            # Process and save results
            urls_scraped = []
            webpage_contents = {}
            
            for crawl_result in crawl_data['crawl_results']:
                # Save to database
                scraped_page = ScrapedPage.objects.create(
                    job=job,
                    url=crawl_result.url,
                    title=crawl_result.title or '',
                    content=crawl_result.content,
                    html_content=getattr(crawl_result, 'html_content', ''),
                    status_code=crawl_result.status_code,
                    file_size=len(crawl_result.content.encode('utf-8')),
                    robots_allowed=crawl_result.robots_allowed,
                    crawl_delay_used=crawl_result.crawl_delay,
                    processing_time=crawl_result.processing_time,
                    crawl_depth=getattr(crawl_result, 'crawl_depth', 0),
                    crawl_status=crawl_result.status,
                    error_message=crawl_result.error_message or ''
                )
                
                # Build response data
                url_data = {
                    'url': crawl_result.url,
                    'title': crawl_result.title,
                    'status_code': crawl_result.status_code,
                    'content_length': len(crawl_result.content),
                    'crawl_depth': getattr(crawl_result, 'crawl_depth', 0),
                    'robots_allowed': crawl_result.robots_allowed,
                    'processing_time': crawl_result.processing_time,
                    'timestamp': timezone.now().isoformat()
                }
                
                urls_scraped.append(url_data)
                webpage_contents[crawl_result.url] = crawl_result.content
            
            # Update job status
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.pages_scraped = len(urls_scraped)
            job.save()
            
            processing_time = (timezone.now() - start_time).total_seconds()
            
            return EnterpriseScrapeResponse(
                starting_domain=request.domain,
                urls_scraped=urls_scraped,
                webpage_contents=webpage_contents,
                job_id=str(job.id),
                status='success',
                total_pages=len(urls_scraped),
                successful_pages=len([u for u in urls_scraped if u.get('status_code') == 200]),
                processing_time_seconds=processing_time,
                timestamp=timezone.now().isoformat(),
                metadata={
                    'batch_id': batch_id,
                    'starting_path': request.starting_path,
                    'max_depth': request.max_depth,
                    'crawler_type': 'agora_enterprise',
                    'include_subdomains': request.include_subdomains,
                    'path_patterns': request.path_patterns
                }
            )
            
        except Exception as e:
            logger.error(f"Enterprise scraping failed for {request.domain}: {str(e)}")
            
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            
            raise e


# Global batch processor instance
batch_processor = EnterpriseBatchProcessor()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enterprise_batch_scrape(request):
    """
    Enterprise batch scraping endpoint.
    
    POST /api/enterprise/batch-scrape/
    
    Body:
    {
        "requests": [
            {
                "domain": "example.com",
                "starting_path": "/api/docs",
                "max_depth": 3,
                "max_pages": 50,
                "frequency_hours": 12,
                "include_subdomains": false,
                "path_patterns": ["/api/*", "/docs/*"],
                "exclude_patterns": ["/private/*"],
                "priority": "high"
            }
        ]
    }
    """
    try:
        data = request.data
        
        # Parse requests
        requests = []
        for req_data in data.get('requests', []):
            req = EnterpriseScrapeRequest(**req_data)
            requests.append(req)
        
        if not requests:
            return Response({
                'error': 'No scraping requests provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process batch asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                batch_processor.process_batch_request(requests)
            )
        finally:
            loop.close()
        
        return Response(result, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Enterprise batch processing failed: {str(e)}")
        return Response({
            'error': 'Batch processing failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enterprise_single_scrape(request):
    """
    Enterprise single domain scraping endpoint.
    
    Returns exact format you requested:
    {
        "starting_domain": "example.com",
        "urls_scraped": [...],
        "webpage_contents": {"url": "text content", ...},
        "job_id": "uuid",
        "status": "success",
        ...
    }
    """
    try:
        data = request.data
        
        # Create enterprise request
        scrape_request = EnterpriseScrapeRequest(**data)
        
        # Process single request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                batch_processor._process_single_request(scrape_request, str(uuid.uuid4()))
            )
        finally:
            loop.close()
        
        # Convert to dict for JSON response
        response_data = asdict(result)
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Enterprise single scraping failed: {str(e)}")
        return Response({
            'error': 'Single scraping failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enterprise_job_status(request, job_id):
    """Get real-time status of enterprise scraping job."""
    try:
        job = ScrapingJob.objects.get(id=job_id)
        
        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'domain': job.domain.domain,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'pages_scraped': job.pages_scraped,
            'pages_failed': job.pages_failed,
            'processing_time': job.duration.total_seconds() if job.duration else None,
            'error_message': job.error_message
        }, status=status.HTTP_200_OK)
        
    except ScrapingJob.DoesNotExist:
        return Response({
            'error': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enterprise_job_results(request, job_id):
    """Get complete results for enterprise scraping job in standardized format."""
    try:
        job = ScrapingJob.objects.get(id=job_id)
        pages = job.scraped_pages.all()
        
        urls_scraped = []
        webpage_contents = {}
        
        for page in pages:
            url_data = {
                'url': page.url,
                'title': page.title,
                'status_code': page.status_code,
                'content_length': page.file_size,
                'crawl_depth': page.crawl_depth,
                'robots_allowed': page.robots_allowed,
                'processing_time': page.processing_time,
                'timestamp': page.created_at.isoformat()
            }
            
            urls_scraped.append(url_data)
            webpage_contents[page.url] = page.content
        
        response = {
            'starting_domain': job.domain.domain,
            'urls_scraped': urls_scraped,
            'webpage_contents': webpage_contents,
            'job_id': str(job.id),
            'status': 'success' if job.status == 'completed' else job.status,
            'total_pages': len(urls_scraped),
            'successful_pages': len([u for u in urls_scraped if u.get('status_code') == 200]),
            'processing_time_seconds': job.duration.total_seconds() if job.duration else 0,
            'timestamp': job.completed_at.isoformat() if job.completed_at else job.created_at.isoformat(),
            'metadata': job.job_config
        }
        
        return Response(response, status=status.HTTP_200_OK)
        
    except ScrapingJob.DoesNotExist:
        return Response({
            'error': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
