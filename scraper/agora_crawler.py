"""
Enhanced Agora Crawler Service
Enterprise-grade web crawler with robots.txt compliance and intelligent crawling capabilities.
Integrated with Django platform for seamless operation.
"""

import httpx
import time
import logging
import validators
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup
from protego import Protego
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Status constants
CRAWL_SUCCESS = "success"
CRAWL_FAILED = "failed"
CRAWL_ROBOTS_BLOCKED = "robots_blocked"
CRAWL_INVALID_URL = "invalid_url"


@dataclass
class CrawlResult:
    """Data structure for individual crawl results."""
    url: str
    title: Optional[str]
    content: str
    status: str
    children: List[str]
    robots_allowed: bool
    crawl_delay: Optional[float]
    processing_time: float
    status_code: Optional[int]
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


@dataclass
class RobotsInfo:
    """Robots.txt parsing results."""
    crawl_delay: Optional[float]
    request_rate: Optional[Tuple[int, int]]
    preferred_host: Optional[str]
    is_allowed: bool


class AgoraCrawlerService:
    """
    Enterprise-grade crawler service with advanced capabilities:
    - Robots.txt compliance with crawl delays
    - Recursive crawling with depth control
    - Sub-path filtering for domain boundaries
    - High-performance async HTTP client
    - Comprehensive error handling and logging
    """

    def __init__(self, user_agent: str = None, respect_robots: bool = True):
        self.user_agent = user_agent or getattr(settings, 'SCRAPING_CONFIG', {}).get(
            'USER_AGENT', 'AgoraScrapingPlatform/1.0'
        )
        self.respect_robots = respect_robots
        self.timeout = getattr(settings, 'SCRAPING_CONFIG', {}).get('DEFAULT_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'SCRAPING_CONFIG', {}).get('MAX_RETRIES', 3)
        
        # Performance settings
        self.concurrent_requests = getattr(settings, 'SCRAPING_CONFIG', {}).get('CONCURRENT_REQUESTS', 5)
        self.default_crawl_delay = 1.0  # Default 1 second between requests
        
        logger.info(f"AgoraCrawlerService initialized with user_agent: {self.user_agent}")

    def read_robots_txt(self, url: str) -> RobotsInfo:
        """
        Read and parse robots.txt for the given URL domain.
        Returns crawl permissions, delays, and rate limits.
        """
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path

        robots_url = urlunparse((scheme, netloc, "/robots.txt", "", "", ""))

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(robots_url, headers={
                    'User-Agent': self.user_agent
                })
                response.raise_for_status()
                robotstxt = response.text
                
            logger.debug(f"Successfully read robots.txt from {robots_url}")

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Could not read robots.txt from {robots_url}: {e}")
            # Default to allowed if robots.txt is not accessible
            return RobotsInfo(
                crawl_delay=self.default_crawl_delay,
                request_rate=None,
                preferred_host=None,
                is_allowed=True
            )

        try:
            rp = Protego.parse(robotstxt)
            
            crawl_delay = rp.crawl_delay(self.user_agent)
            request_rate = rp.request_rate(self.user_agent)
            preferred_host = rp.preferred_host
            is_allowed = rp.can_fetch(url, self.user_agent)

            if request_rate:
                request_rate = (request_rate.requests, request_rate.seconds)

            return RobotsInfo(
                crawl_delay=crawl_delay or self.default_crawl_delay,
                request_rate=request_rate,
                preferred_host=preferred_host,
                is_allowed=is_allowed
            )

        except Exception as e:
            logger.error(f"Error parsing robots.txt: {e}")
            return RobotsInfo(
                crawl_delay=self.default_crawl_delay,
                request_rate=None,
                preferred_host=None,
                is_allowed=True
            )

    def is_sub_path(self, link: str, parent_url: str) -> bool:
        """
        Check if a link is a sub-path of the parent URL.
        Ensures crawling stays within domain boundaries.
        """
        try:
            parsed_link = urlparse(link)
            parsed_parent = urlparse(parent_url)

            # Different domain
            if parsed_link.netloc != parsed_parent.netloc:
                return False

            link_path = parsed_link.path.rstrip("/")
            parent_path = parsed_parent.path.rstrip("/")

            # Not a subpath
            if not link_path.startswith(parent_path):
                return False

            # Exact match
            if link_path == parent_path:
                return True

            # Proper subpath (with directory separator)
            return link_path[len(parent_path)] == "/"

        except Exception as e:
            logger.warning(f"Error checking sub-path for {link}: {e}")
            return False

    def extract_child_links(self, soup: BeautifulSoup, parent_url: str) -> List[str]:
        """
        Extract and validate child links from HTML content.
        Converts relative URLs to absolute and filters sub-paths.
        """
        try:
            # Extract all href attributes
            raw_links = [link.get("href") for link in soup.find_all("a", href=True)]
            
            # Convert relative URLs to absolute
            absolute_links = []
            for link in raw_links:
                if link:
                    if link.startswith("/"):
                        # Relative to domain root
                        parsed_parent = urlparse(parent_url)
                        absolute_url = urlunparse((
                            parsed_parent.scheme,
                            parsed_parent.netloc,
                            link,
                            "", "", ""
                        ))
                        absolute_links.append(absolute_url)
                    elif link.startswith(("http://", "https://")):
                        # Already absolute
                        absolute_links.append(link)
                    elif not link.startswith(("#", "mailto:", "tel:")):
                        # Relative to current path
                        absolute_links.append(urljoin(parent_url, link))

            # Filter to only sub-paths of parent URL
            valid_children = [
                link for link in absolute_links 
                if self.is_sub_path(link, parent_url) and validators.url(link)
            ]

            # Remove duplicates while preserving order
            seen = set()
            unique_children = []
            for link in valid_children:
                if link not in seen:
                    seen.add(link)
                    unique_children.append(link)

            return unique_children

        except Exception as e:
            logger.error(f"Error extracting child links: {e}")
            return []

    def parse_html_content(self, html_content: str, parent_url: str) -> Tuple[Optional[str], List[str], str]:
        """
        Parse HTML content to extract title, child links, and text content.
        Uses BeautifulSoup for robust HTML parsing.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title
            title_element = soup.find("title")
            title = title_element.string.strip() if title_element and title_element.string else None

            # Extract child links
            child_links = self.extract_child_links(soup, parent_url)

            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text_content = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = ' '.join(chunk for chunk in chunks if chunk)

            return title, child_links, content

        except Exception as e:
            logger.error(f"Error parsing HTML content: {e}")
            return None, [], ""

    def validate_url(self, url: str) -> bool:
        """Validate URL format using validators library."""
        try:
            return validators.url(url) is True
        except Exception:
            return False

    def fetch_url(self, url: str) -> CrawlResult:
        """
        Fetch content from a single URL with full error handling and robots.txt compliance.
        """
        start_time = time.time()
        
        # Validate URL
        if not self.validate_url(url):
            return CrawlResult(
                url=url,
                title=None,
                content="",
                status=CRAWL_INVALID_URL,
                children=[],
                robots_allowed=False,
                crawl_delay=None,
                processing_time=time.time() - start_time,
                status_code=None,
                error_message="Invalid URL format"
            )

        # Check robots.txt compliance
        robots_info = None
        if self.respect_robots:
            robots_info = self.read_robots_txt(url)
            
            if not robots_info.is_allowed:
                return CrawlResult(
                    url=url,
                    title=None,
                    content="",
                    status=CRAWL_ROBOTS_BLOCKED,
                    children=[],
                    robots_allowed=False,
                    crawl_delay=robots_info.crawl_delay,
                    processing_time=time.time() - start_time,
                    status_code=None,
                    error_message="Blocked by robots.txt"
                )

            # Respect crawl delay
            if robots_info.crawl_delay:
                logger.debug(f"Applying crawl delay of {robots_info.crawl_delay}s for {url}")
                time.sleep(robots_info.crawl_delay)

        # Perform HTTP request
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    url,
                    headers={'User-Agent': self.user_agent},
                    follow_redirects=True
                )

                if response.status_code == 200:
                    # Parse successful response
                    title, child_links, content = self.parse_html_content(response.text, url)
                    
                    return CrawlResult(
                        url=url,
                        title=title,
                        content=content,
                        status=CRAWL_SUCCESS,
                        children=child_links,
                        robots_allowed=robots_info.is_allowed if robots_info else True,
                        crawl_delay=robots_info.crawl_delay if robots_info else None,
                        processing_time=time.time() - start_time,
                        status_code=response.status_code
                    )
                else:
                    return CrawlResult(
                        url=url,
                        title=None,
                        content="",
                        status=CRAWL_FAILED,
                        children=[],
                        robots_allowed=robots_info.is_allowed if robots_info else True,
                        crawl_delay=robots_info.crawl_delay if robots_info else None,
                        processing_time=time.time() - start_time,
                        status_code=response.status_code,
                        error_message=f"HTTP {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return CrawlResult(
                url=url,
                title=None,
                content="",
                status=CRAWL_FAILED,
                children=[],
                robots_allowed=robots_info.is_allowed if robots_info else True,
                crawl_delay=robots_info.crawl_delay if robots_info else None,
                processing_time=time.time() - start_time,
                status_code=None,
                error_message=str(e)
            )

    def crawl_url_batch(self, urls: List[str]) -> Tuple[List[str], List[CrawlResult]]:
        """
        Crawl a batch of URLs and collect results.
        Returns child links and crawl results.
        """
        crawled_results = []
        all_child_links = []

        for url in urls:
            logger.info(f"Crawling: {url}")
            result = self.fetch_url(url)
            
            if result.status == CRAWL_SUCCESS:
                crawled_results.append(result)
                all_child_links.extend(result.children)
                logger.info(f"Successfully crawled {url}: {len(result.children)} children found")
            else:
                crawled_results.append(result)
                logger.warning(f"Failed to crawl {url}: {result.error_message}")

        # Remove duplicate child links
        unique_child_links = list(set(all_child_links))
        
        return unique_child_links, crawled_results

    def crawl_recursive(self, start_url: str, max_depth: int = 2, max_pages_per_level: int = 50) -> Dict[str, Any]:
        """
        Perform recursive crawling starting from a URL.
        
        Args:
            start_url: The starting URL for crawling
            max_depth: Maximum recursion depth
            max_pages_per_level: Maximum pages to crawl per depth level
            
        Returns:
            Dictionary containing all crawl results and metadata
        """
        if not self.validate_url(start_url):
            return {
                "error": "Invalid start URL",
                "crawl_results": [],
                "child_links": [],
                "total_pages": 0,
                "processing_time": 0
            }

        start_time = time.time()
        logger.info(f"Starting recursive crawl of {start_url} with max_depth={max_depth}")

        all_crawl_results = []
        all_child_links = set()
        current_level = [start_url]

        for depth in range(max_depth):
            if not current_level:
                break

            logger.info(f"Crawling depth {depth + 1}/{max_depth}: {len(current_level)} URLs")
            
            # Limit URLs per level to prevent runaway crawling
            limited_urls = current_level[:max_pages_per_level]
            if len(current_level) > max_pages_per_level:
                logger.warning(f"Limited crawling to {max_pages_per_level} URLs at depth {depth + 1}")

            # Crawl current level
            child_links, crawl_results = self.crawl_url_batch(limited_urls)
            
            all_crawl_results.extend(crawl_results)
            all_child_links.update(child_links)
            
            # Prepare next level (remove already crawled URLs)
            crawled_urls = {result.url for result in all_crawl_results}
            current_level = [url for url in child_links if url not in crawled_urls]

        total_time = time.time() - start_time
        
        result = {
            "crawl_results": all_crawl_results,
            "child_links": list(all_child_links),
            "total_pages": len(all_crawl_results),
            "successful_pages": len([r for r in all_crawl_results if r.status == CRAWL_SUCCESS]),
            "failed_pages": len([r for r in all_crawl_results if r.status == CRAWL_FAILED]),
            "robots_blocked_pages": len([r for r in all_crawl_results if r.status == CRAWL_ROBOTS_BLOCKED]),
            "processing_time": total_time,
            "start_url": start_url,
            "max_depth": max_depth,
            "timestamp": timezone.now().isoformat()
        }

        logger.info(f"Crawling completed: {result['total_pages']} pages in {total_time:.2f}s")
        return result


# Singleton instance for global use
_agora_crawler_service = None

def get_agora_crawler_service(user_agent: str = None, respect_robots: bool = True) -> AgoraCrawlerService:
    """Get singleton instance of AgoraCrawlerService."""
    global _agora_crawler_service
    if _agora_crawler_service is None:
        _agora_crawler_service = AgoraCrawlerService(user_agent=user_agent, respect_robots=respect_robots)
    return _agora_crawler_service
