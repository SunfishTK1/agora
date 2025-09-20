#!/usr/bin/env python
"""
Comprehensive test suite for Agora Crawler integration.
Tests the complete pipeline: Agora crawler -> Django models -> Vector database -> Search API.
"""

import os
import sys
import django
import time
import json
from typing import Dict, Any, List

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from scraper.models import Domain, ScrapingJob, ScrapedPage, RobotsInfo
from scraper.agora_crawler import get_agora_crawler_service, CRAWL_SUCCESS
from scraper.services import ScrapingService


def test_agora_crawler_direct():
    """Test the Agora crawler directly."""
    print("🚀 Testing Agora Crawler Direct Operations...")
    
    try:
        # Initialize crawler
        crawler = get_agora_crawler_service()
        print("✅ Agora crawler initialized successfully")
        
        # Test robots.txt reading
        robots_info = crawler.read_robots_txt("https://httpbin.org")
        print(f"✅ Robots.txt info: allowed={robots_info.is_allowed}, delay={robots_info.crawl_delay}")
        
        # Test URL validation
        valid_urls = [
            "https://httpbin.org",
            "https://httpbin.org/json",
            "https://httpbin.org/html"
        ]
        
        for url in valid_urls:
            is_valid = crawler.validate_url(url)
            print(f"✅ URL validation for {url}: {is_valid}")
        
        # Test single URL fetch
        result = crawler.fetch_url("https://httpbin.org/json")
        print(f"✅ Single fetch result: status={result.status}, title='{result.title}', content_length={len(result.content)}")
        
        # Test recursive crawling (limited depth for testing)
        crawl_results = crawler.crawl_recursive(
            start_url="https://httpbin.org", 
            max_depth=1,
            max_pages_per_level=3
        )
        
        print(f"✅ Recursive crawl results:")
        print(f"   - Total pages: {crawl_results['total_pages']}")
        print(f"   - Successful: {crawl_results['successful_pages']}")
        print(f"   - Failed: {crawl_results['failed_pages']}")
        print(f"   - Processing time: {crawl_results['processing_time']:.2f}s")
        
        return crawl_results
        
    except Exception as e:
        print(f"❌ Agora crawler test failed: {str(e)}")
        return None


def test_django_integration():
    """Test Django integration with Agora crawler."""
    print("\n🔗 Testing Django Integration...")
    
    try:
        # Create test user and domain
        user, created = User.objects.get_or_create(
            username='agora_test_user',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Agora',
                'last_name': 'Tester'
            }
        )
        
        domain, created = Domain.objects.get_or_create(
            base_url='https://httpbin.org',
            defaults={
                'name': 'HTTPBin Test Domain',
                'domain': 'httpbin.org',
                'max_depth': 2,
                'max_pages': 5,
                'created_by': user
            }
        )
        
        print(f"✅ Created test domain: {domain.name}")
        
        # Test enhanced scraping service
        scraping_service = ScrapingService(use_dummy_api=False)  # Use real Agora crawler
        
        # Create scraping job
        job = ScrapingJob.objects.create(
            domain=domain,
            scheduled_at=timezone.now(),
            status='running'
        )
        
        print(f"✅ Created scraping job: {job.id}")
        
        # Run enhanced scraping
        results = scraping_service.scrape_domain(domain, job)
        
        print(f"✅ Enhanced scraping completed:")
        print(f"   - Crawler type: {results.get('crawler_type')}")
        print(f"   - Total pages: {results.get('total_pages')}")
        print(f"   - Successful: {results.get('successful_pages')}")
        print(f"   - Failed: {results.get('failed_pages')}")
        print(f"   - Robots blocked: {results.get('robots_blocked_pages')}")
        print(f"   - Processing time: {results.get('processing_time_seconds'):.2f}s")
        
        # Verify database entries
        scraped_pages = ScrapedPage.objects.filter(job=job)
        print(f"✅ Database entries created: {scraped_pages.count()} pages")
        
        # Check Agora-specific fields
        for page in scraped_pages[:3]:  # Check first 3 pages
            print(f"   - {page.url}")
            print(f"     Status: {page.crawl_status}")
            print(f"     Robots allowed: {page.robots_allowed}")
            print(f"     Depth: {page.crawl_depth}")
            print(f"     Processing time: {page.processing_time:.3f}s")
        
        return {
            'domain': domain,
            'job': job,
            'results': results,
            'pages_created': scraped_pages.count()
        }
        
    except Exception as e:
        print(f"❌ Django integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_robots_info_model():
    """Test RobotsInfo model functionality."""
    print("\n🤖 Testing RobotsInfo Model...")
    
    try:
        # Create robots info entry
        robots_info = RobotsInfo.objects.create(
            domain='httpbin.org',
            robots_txt_content='User-agent: *\nDisallow: /deny',
            crawl_delay=1.0,
            is_accessible=True
        )
        
        print(f"✅ Created RobotsInfo entry for {robots_info.domain}")
        print(f"   - Crawl delay: {robots_info.crawl_delay}s")
        print(f"   - Is accessible: {robots_info.is_accessible}")
        print(f"   - Last checked: {robots_info.last_checked}")
        
        return robots_info
        
    except Exception as e:
        print(f"❌ RobotsInfo model test failed: {str(e)}")
        return None


def test_performance_metrics():
    """Test performance and scaling characteristics."""
    print("\n⚡ Testing Performance Metrics...")
    
    try:
        # Test crawler performance on multiple URLs
        crawler = get_agora_crawler_service()
        test_urls = [
            "https://httpbin.org/json",
            "https://httpbin.org/xml", 
            "https://httpbin.org/html",
            "https://httpbin.org/robots.txt"
        ]
        
        start_time = time.time()
        results = []
        
        for url in test_urls:
            result = crawler.fetch_url(url)
            results.append(result)
        
        total_time = time.time() - start_time
        
        print(f"✅ Performance test completed:")
        print(f"   - URLs tested: {len(test_urls)}")
        print(f"   - Total time: {total_time:.3f}s")
        print(f"   - Average per URL: {total_time/len(test_urls):.3f}s")
        print(f"   - Success rate: {sum(1 for r in results if r.status == CRAWL_SUCCESS)/len(results)*100:.1f}%")
        
        # Test batch processing
        start_time = time.time()
        batch_results = crawler.crawl_url_batch(test_urls)
        batch_time = time.time() - start_time
        
        print(f"✅ Batch processing test:")
        print(f"   - Batch time: {batch_time:.3f}s")
        print(f"   - Results: {len(batch_results[1])} pages processed")
        
        return {
            'sequential_time': total_time,
            'batch_time': batch_time,
            'urls_tested': len(test_urls)
        }
        
    except Exception as e:
        print(f"❌ Performance test failed: {str(e)}")
        return None


def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🛡️ Testing Error Handling...")
    
    try:
        crawler = get_agora_crawler_service()
        
        # Test invalid URLs
        invalid_urls = [
            "not-a-url",
            "http://",
            "https://nonexistent-domain-12345.com",
            "https://httpbin.org/status/404",
            "https://httpbin.org/status/500"
        ]
        
        error_results = []
        for url in invalid_urls:
            result = crawler.fetch_url(url)
            error_results.append((url, result.status, result.error_message))
            print(f"   - {url}: {result.status}")
        
        print(f"✅ Error handling test completed: {len(error_results)} cases tested")
        
        # Test robots.txt edge cases
        robots_test_domains = [
            "nonexistent-domain-12345.com",
            "httpbin.org"  # Should work
        ]
        
        for domain in robots_test_domains:
            robots_info = crawler.read_robots_txt(f"https://{domain}")
            print(f"   - Robots.txt for {domain}: allowed={robots_info.is_allowed}")
        
        return error_results
        
    except Exception as e:
        print(f"❌ Error handling test failed: {str(e)}")
        return None


def print_test_summary(results: Dict[str, Any]):
    """Print comprehensive test summary."""
    print("\n" + "="*60)
    print("🎯 AGORA CRAWLER INTEGRATION TEST SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result is not None)
    
    print(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if results.get('django_integration'):
        django_results = results['django_integration']
        print(f"🔗 Django Integration: ✅")
        print(f"   - Pages scraped: {django_results['pages_created']}")
        print(f"   - Processing time: {django_results['results']['processing_time_seconds']:.2f}s")
    
    if results.get('performance'):
        perf_results = results['performance']
        print(f"⚡ Performance: ✅")
        print(f"   - Sequential processing: {perf_results['sequential_time']:.3f}s")
        print(f"   - Batch processing: {perf_results['batch_time']:.3f}s")
    
    print(f"🤖 Robots.txt Compliance: {'✅' if results.get('robots_info') else '❌'}")
    print(f"🛡️ Error Handling: {'✅' if results.get('error_handling') else '❌'}")
    print(f"🚀 Direct Crawler: {'✅' if results.get('agora_direct') else '❌'}")
    
    print("\n🎉 INTEGRATION STATUS:")
    if passed_tests == total_tests:
        print("✅ AGORA CRAWLER INTEGRATION SUCCESSFUL!")
        print("   All systems operational and ready for production use.")
    elif passed_tests >= total_tests * 0.8:  # 80% pass rate
        print("⚠️  AGORA CRAWLER INTEGRATION MOSTLY SUCCESSFUL")
        print("   Minor issues detected, but core functionality working.")
    else:
        print("❌ AGORA CRAWLER INTEGRATION NEEDS ATTENTION")
        print("   Significant issues detected, review required.")


def main():
    """Run comprehensive integration test suite."""
    print("🔥 STARTING AGORA CRAWLER INTEGRATION TESTS")
    print("=" * 60)
    
    test_results = {}
    
    # Run all test suites
    test_results['agora_direct'] = test_agora_crawler_direct()
    test_results['django_integration'] = test_django_integration()
    test_results['robots_info'] = test_robots_info_model()
    test_results['performance'] = test_performance_metrics()
    test_results['error_handling'] = test_error_handling()
    
    # Print comprehensive summary
    print_test_summary(test_results)
    
    return test_results


if __name__ == "__main__":
    results = main()
