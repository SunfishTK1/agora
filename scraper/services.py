"""
Scraping services with enterprise-grade architecture.
Includes dummy API calls, error handling, and extensible design.
"""

import time
import uuid
import json
import hashlib
import logging
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from .models import Domain, ScrapingJob, ScrapedPage, ApiEndpoint, SystemMetrics

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Data structure for scraping results."""
    url: str
    title: str
    content: str
    raw_html: str
    status_code: int
    content_type: str
    content_length: int
    links_found: int
    internal_links: int
    external_links: int
    processing_time_ms: int
    extracted_data: Dict[str, Any]
    error_message: str = ""


class ScrapingService:
    """
    Enterprise-grade scraping service with configurable backends.
    Supports real scraping and dummy API mode.
    """
    
    def __init__(self, use_dummy_api: bool = True):
        self.use_dummy_api = use_dummy_api
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.SCRAPING_CONFIG.get('USER_AGENT', 'ScrapingPlatform/1.0')
        })
        
        # Configure session
        self.timeout = settings.SCRAPING_CONFIG.get('DEFAULT_TIMEOUT', 30)
        self.max_retries = settings.SCRAPING_CONFIG.get('MAX_RETRIES', 3)
        self.retry_delay = settings.SCRAPING_CONFIG.get('RETRY_DELAY', 5)
        
        # Initialize summarization pipeline if enabled in settings
        self.enable_auto_summarization = getattr(settings, 'ENABLE_AUTO_SUMMARIZATION', True)
        if self.enable_auto_summarization:
            try:
                from .summarization_pipeline import SummarizationPipeline
                self.summarization_pipeline = SummarizationPipeline()
            except ImportError:
                logger.warning("Summarization pipeline not available, disabling auto-summarization")
                self.enable_auto_summarization = False
        
    def scrape_domain(self, domain: Domain, job: ScrapingJob) -> Dict[str, Any]:
        """
        Main entry point for domain scraping.
        Returns a dictionary with scraping results.
        """
        logger.info(f"Starting scrape for domain: {domain.name} (Job: {job.id})")
        
        start_time = timezone.now()
        results = {
            'domain': domain.domain,
            'base_url': domain.base_url,
            'job_id': str(job.id),
            'started_at': start_time.isoformat(),
            'pages': [],
            'summary': {
                'total_pages': 0,
                'successful_pages': 0,
                'failed_pages': 0,
                'total_size_bytes': 0,
                'processing_time_seconds': 0
            }
        }
        
        try:
            # Update job status
            job.status = 'running'
            job.started_at = start_time
            job.save()
            
            if self.use_dummy_api:
                pages_data = self._dummy_scrape_pages(domain, job)
            else:
                pages_data = self._real_scrape_pages(domain, job)
            
            # Process each page result
            for page_data in pages_data:
                try:
                    scraped_page = self._save_scraped_page(job, page_data)
                    
                    # Add to results
                    page_result = {
                        'url': page_data.url,
                        'title': page_data.title,
                        'content': page_data.content[:1000] + "..." if len(page_data.content) > 1000 else page_data.content,
                        'status_code': page_data.status_code,
                        'content_length': page_data.content_length,
                        'extracted_data': page_data.extracted_data
                    }
                    results['pages'].append(page_result)
                    
                    # Update summary
                    results['summary']['total_pages'] += 1
                    if page_data.status_code == 200:
                        results['summary']['successful_pages'] += 1
                    else:
                        results['summary']['failed_pages'] += 1
                    results['summary']['total_size_bytes'] += page_data.content_length
                    
                except Exception as e:
                    logger.error(f"Error saving page {page_data.url}: {str(e)}")
                    results['summary']['failed_pages'] += 1
            
            # Complete the job
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            job.status = 'completed'
            job.completed_at = end_time
            job.pages_scraped = results['summary']['successful_pages']
            job.pages_failed = results['summary']['failed_pages']
            job.total_size_bytes = results['summary']['total_size_bytes']
            job.save()
            
            # Update domain statistics
            domain.total_scrapes += 1
            domain.successful_scrapes += 1
            domain.last_scraped = end_time
            domain.next_scrape = domain.get_next_scrape_time()
            domain.save()
            
            results['summary']['processing_time_seconds'] = duration
            results['completed_at'] = end_time.isoformat()
            results['status'] = 'success'
            
            logger.info(f"Scraping completed for {domain.name}: {results['summary']}")
            
            # Auto-trigger summarization pipeline if enabled
            if self.enable_auto_summarization and results['summary']['successful_pages'] > 0:
                try:
                    logger.info(f"Starting auto-summarization for job {job.id}")
                    summarization_stats = self.summarization_pipeline.process_scraped_pages(
                        job_id=str(job.id)
                    )
                    results['summarization_stats'] = summarization_stats
                    logger.info(f"Auto-summarization completed: {summarization_stats}")
                except Exception as e:
                    logger.error(f"Auto-summarization failed for job {job.id}: {str(e)}")
                    results['summarization_error'] = str(e)
            
            return results
            
        except Exception as e:
            logger.error(f"Scraping failed for {domain.name}: {str(e)}")
            
            # Update job with error
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            
            # Update domain statistics
            domain.failed_scrapes += 1
            domain.save()
            
            results['status'] = 'error'
            results['error'] = str(e)
            results['completed_at'] = timezone.now().isoformat()
            
            return results
    
    def _dummy_scrape_pages(self, domain: Domain, job: ScrapingJob) -> List[ScrapingResult]:
        """
        Dummy scraping implementation for testing and development.
        Generates realistic fake data.
        """
        logger.info(f"Using dummy API for scraping {domain.base_url}")
        
        pages = []
        base_url = domain.base_url
        parsed_base = urlparse(base_url)
        
        # Generate a realistic number of pages
        num_pages = min(random.randint(5, 50), domain.max_pages)
        
        for i in range(num_pages):
            # Simulate processing time
            time.sleep(random.uniform(0.1, 0.5))
            
            # Generate realistic URLs
            depth = random.randint(0, domain.max_depth)
            path_segments = []
            for d in range(depth):
                segments = ['products', 'services', 'blog', 'news', 'docs', 'api', 'help']
                path_segments.append(random.choice(segments))
                if d < depth - 1:
                    path_segments.append(f'item-{random.randint(1, 100)}')
            
            if path_segments:
                url = urljoin(base_url, '/'.join(path_segments))
            else:
                url = base_url
            
            # Generate realistic content
            titles = [
                f"Understanding {random.choice(['AI', 'ML', 'Data Science', 'Analytics'])}",
                f"Best Practices for {random.choice(['Development', 'Testing', 'Deployment'])}",
                f"Introduction to {random.choice(['Python', 'Django', 'React', 'APIs'])}",
                f"Advanced {random.choice(['Techniques', 'Strategies', 'Methods'])}"
            ]
            
            content_templates = [
                "This is a comprehensive guide about {topic}. It covers all the essential aspects including implementation details, best practices, and real-world examples. The content is structured to provide maximum value to readers.",
                "Welcome to our detailed analysis of {topic}. In this article, we explore the fundamentals, advanced concepts, and practical applications. Our team has compiled insights from industry experts.",
                "Learn everything you need to know about {topic}. This resource includes step-by-step instructions, code examples, and troubleshooting tips to help you succeed in your projects."
            ]
            
            title = random.choice(titles)
            topic = title.split()[-1]
            content_template = random.choice(content_templates)
            content = content_template.format(topic=topic)
            content = content + " " * random.randint(100, 1000)  # Variable length
            
            # Generate HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <h1>{title}</h1>
                <div class="content">
                    <p>{content}</p>
                </div>
                <nav>
                    {''.join([f'<a href="/link-{j}">Link {j}</a>' for j in range(random.randint(3, 10))])}
                </nav>
            </body>
            </html>
            """
            
            # Simulate extracted structured data
            extracted_data = {
                'title': title,
                'meta_description': content[:150] + "...",
                'headings': [title] + [f"Section {j}" for j in range(random.randint(2, 5))],
                'links': [f"/link-{j}" for j in range(random.randint(5, 15))],
                'images': [f"/images/img-{j}.jpg" for j in range(random.randint(0, 5))],
                'word_count': len(content.split()),
                'language': 'en',
                'last_updated': (timezone.now() - timedelta(days=random.randint(1, 30))).isoformat()
            }
            
            # Create scraping result
            processing_time = random.randint(100, 2000)
            content_length = len(html_content)
            links_found = random.randint(5, 20)
            
            result = ScrapingResult(
                url=url,
                title=title,
                content=content,
                raw_html=html_content,
                status_code=200 if random.random() > 0.05 else random.choice([404, 500, 503]),
                content_type='text/html',
                content_length=content_length,
                links_found=links_found,
                internal_links=random.randint(2, links_found - 2),
                external_links=random.randint(0, 3),
                processing_time_ms=processing_time,
                extracted_data=extracted_data
            )
            
            pages.append(result)
        
        return pages
    
    def _real_scrape_pages(self, domain: Domain, job: ScrapingJob) -> List[ScrapingResult]:
        """
        Real scraping implementation using requests and BeautifulSoup.
        """
        logger.info(f"Starting real scraping for {domain.base_url}")
        
        pages = []
        visited_urls = set()
        urls_to_visit = [(domain.base_url, 0)]  # (url, depth)
        
        while urls_to_visit and len(pages) < domain.max_pages:
            url, depth = urls_to_visit.pop(0)
            
            if url in visited_urls or depth > domain.max_depth:
                continue
                
            visited_urls.add(url)
            
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=self.timeout)
                processing_time = int((time.time() - start_time) * 1000)
                
                # Parse content
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.find('title').get_text().strip() if soup.find('title') else ""
                
                # Extract text content
                for script in soup(["script", "style"]):
                    script.decompose()
                content = soup.get_text()
                content = ' '.join(content.split())  # Clean whitespace
                
                # Find links for further crawling
                if depth < domain.max_depth:
                    links = soup.find_all('a', href=True)
                    for link in links[:10]:  # Limit links per page
                        href = link['href']
                        full_url = urljoin(url, href)
                        parsed = urlparse(full_url)
                        
                        # Only follow same-domain links
                        if parsed.netloc == urlparse(domain.base_url).netloc:
                            urls_to_visit.append((full_url, depth + 1))
                
                # Extract structured data
                extracted_data = self._extract_structured_data(soup, url)
                
                # Count links
                all_links = soup.find_all('a', href=True)
                internal_links = sum(1 for link in all_links 
                                   if urlparse(urljoin(url, link['href'])).netloc == urlparse(url).netloc)
                external_links = len(all_links) - internal_links
                
                result = ScrapingResult(
                    url=url,
                    title=title,
                    content=content,
                    raw_html=str(response.content, 'utf-8', errors='ignore'),
                    status_code=response.status_code,
                    content_type=response.headers.get('content-type', ''),
                    content_length=len(response.content),
                    links_found=len(all_links),
                    internal_links=internal_links,
                    external_links=external_links,
                    processing_time_ms=processing_time,
                    extracted_data=extracted_data
                )
                
                pages.append(result)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                
                result = ScrapingResult(
                    url=url,
                    title="",
                    content="",
                    raw_html="",
                    status_code=0,
                    content_type="",
                    content_length=0,
                    links_found=0,
                    internal_links=0,
                    external_links=0,
                    processing_time_ms=0,
                    extracted_data={},
                    error_message=str(e)
                )
                pages.append(result)
        
        return pages
    
    def _extract_structured_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract structured data from parsed HTML."""
        data = {}
        
        try:
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                data['meta_description'] = meta_desc.get('content', '')
            
            # Headings
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for heading in soup.find_all(tag):
                    headings.append({
                        'level': int(tag[1]),
                        'text': heading.get_text().strip()
                    })
            data['headings'] = headings
            
            # Images
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    images.append({
                        'src': urljoin(url, src),
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    })
            data['images'] = images
            
            # Links
            links = []
            for link in soup.find_all('a', href=True):
                links.append({
                    'href': urljoin(url, link['href']),
                    'text': link.get_text().strip(),
                    'title': link.get('title', '')
                })
            data['links'] = links[:50]  # Limit to 50 links
            
            # Language
            html_tag = soup.find('html')
            if html_tag:
                data['language'] = html_tag.get('lang', 'unknown')
            
            # Word count
            text_content = soup.get_text()
            data['word_count'] = len(text_content.split())
            
        except Exception as e:
            logger.warning(f"Error extracting structured data from {url}: {str(e)}")
            
        return data
    
    def _save_scraped_page(self, job: ScrapingJob, result: ScrapingResult) -> ScrapedPage:
        """Save scraping result to database."""
        
        # Determine depth level from URL
        base_parts = urlparse(job.domain.base_url).path.strip('/').split('/')
        url_parts = urlparse(result.url).path.strip('/').split('/')
        depth_level = max(0, len(url_parts) - len(base_parts))
        
        # Determine status
        if result.error_message:
            status = 'failed'
        elif result.status_code == 200:
            status = 'success'
        else:
            status = 'failed'
        
        scraped_page = ScrapedPage.objects.create(
            job=job,
            url=result.url,
            depth_level=depth_level,
            title=result.title,
            content=result.content,
            raw_html=result.raw_html,
            status_code=result.status_code or None,
            content_type=result.content_type,
            content_length=result.content_length or None,
            status=status,
            processing_time_ms=result.processing_time_ms or None,
            error_message=result.error_message,
            extracted_data=result.extracted_data,
            links_found=result.links_found,
            internal_links=result.internal_links,
            external_links=result.external_links
        )
        
        return scraped_page


class ApiIntegrationService:
    """
    Service for integrating with external APIs.
    Handles authentication, rate limiting, and error handling.
    """
    
    def __init__(self):
        self.session = requests.Session()
        
    def send_scraping_results(self, results: Dict[str, Any], endpoint: ApiEndpoint) -> Dict[str, Any]:
        """Send scraping results to external API endpoint."""
        
        try:
            logger.info(f"Sending results to API endpoint: {endpoint.name}")
            
            # Prepare headers
            headers = dict(endpoint.headers)
            headers.setdefault('Content-Type', 'application/json')
            
            # Handle authentication
            if endpoint.auth_type == 'bearer':
                token = endpoint.auth_config.get('token')
                if token:
                    headers['Authorization'] = f'Bearer {token}'
            elif endpoint.auth_type == 'api_key':
                key_name = endpoint.auth_config.get('key_name', 'X-API-Key')
                api_key = endpoint.auth_config.get('api_key')
                if api_key:
                    headers[key_name] = api_key
            
            # Make request
            response = self.session.request(
                method=endpoint.method,
                url=endpoint.endpoint_url,
                json=results,
                headers=headers,
                timeout=endpoint.timeout
            )
            
            # Update endpoint usage
            endpoint.last_used = timezone.now()
            endpoint.save()
            
            response.raise_for_status()
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response': response.json() if response.content else {},
                'endpoint': endpoint.name
            }
            
        except Exception as e:
            logger.error(f"Error sending to API endpoint {endpoint.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'endpoint': endpoint.name
            }


class MetricsCollector:
    """Collect and store system metrics."""
    
    @staticmethod
    def record_scraping_metrics(job: ScrapingJob):
        """Record metrics after job completion."""
        
        if job.status != 'completed':
            return
            
        try:
            duration = job.duration
            if duration:
                SystemMetrics.objects.create(
                    metric_name='job_duration_seconds',
                    metric_value=duration.total_seconds(),
                    metric_unit='seconds',
                    context_data={'job_id': str(job.id), 'domain': job.domain.domain}
                )
            
            # Pages per second
            if duration and job.pages_scraped > 0:
                pages_per_second = job.pages_scraped / duration.total_seconds()
                SystemMetrics.objects.create(
                    metric_name='pages_per_second',
                    metric_value=pages_per_second,
                    metric_unit='pages/sec',
                    context_data={'job_id': str(job.id), 'domain': job.domain.domain}
                )
            
            # Success rate
            total_pages = job.pages_scraped + job.pages_failed
            if total_pages > 0:
                success_rate = (job.pages_scraped / total_pages) * 100
                SystemMetrics.objects.create(
                    metric_name='job_success_rate',
                    metric_value=success_rate,
                    metric_unit='percent',
                    context_data={'job_id': str(job.id), 'domain': job.domain.domain}
                )
            
        except Exception as e:
            logger.error(f"Error recording metrics for job {job.id}: {str(e)}")
