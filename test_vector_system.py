#!/usr/bin/env python
"""
Test script for the vector database system.
Demonstrates the complete workflow from scraping to semantic search.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

import json
import time
from django.contrib.auth.models import User
from scraper.models import Domain, ScrapingJob, ScrapedPage, PageSummary, DocumentEmbedding
from scraper.services import ScrapingService
from scraper.summarization_pipeline import SummarizationPipeline
from scraper.ai_services import AzureOpenAIEmbeddingService
from scraper.milvus_service import get_milvus_service


def create_test_data():
    """Create test data for demonstration."""
    print("🚀 Creating test data...")
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com'}
    )
    
    # Create test domain
    domain, created = Domain.objects.get_or_create(
        base_url='https://example.com',
        defaults={
            'name': 'Example Domain',
            'domain': 'example.com',
            'max_depth': 2,
            'max_pages': 10,
            'created_by': user
        }
    )
    
    print(f"✅ Created domain: {domain.name}")
    return domain, user


def run_scraping_test(domain):
    """Test the scraping workflow."""
    print("🕷️  Testing scraping workflow...")
    
    # Create scraping job
    job = ScrapingJob.objects.create(
        domain=domain,
        job_type='manual',
        priority='high'
    )
    
    # Run scraping service in dummy mode
    scraping_service = ScrapingService(use_dummy_api=True)
    results = scraping_service.scrape_domain(domain, job)
    
    print(f"✅ Scraping completed: {results['summary']['successful_pages']} pages scraped")
    print(f"   Processing time: {results['summary']['processing_time_seconds']:.2f}s")
    
    if 'summarization_stats' in results:
        print(f"   Summarization: {results['summarization_stats']['successful_summaries']} summaries created")
        print(f"   Embeddings: {results['summarization_stats']['successful_embeddings']} embeddings created")
    
    return job


def test_manual_summarization(job):
    """Test manual summarization pipeline."""
    print("📝 Testing manual summarization...")
    
    pipeline = SummarizationPipeline()
    stats = pipeline.process_scraped_pages(job_id=str(job.id))
    
    print(f"✅ Manual summarization completed:")
    print(f"   Processed pages: {stats['processed_pages']}")
    print(f"   Successful summaries: {stats['successful_summaries']}")
    print(f"   Successful embeddings: {stats['successful_embeddings']}")
    print(f"   Total time: {stats['total_processing_time']:.2f}s")
    
    return stats


def test_vector_search():
    """Test vector search functionality."""
    print("🔍 Testing vector search...")
    
    try:
        # Test embedding service
        embedding_service = AzureOpenAIEmbeddingService()
        test_query = "artificial intelligence and machine learning applications"
        query_embedding = embedding_service.generate_embedding(test_query)
        
        print(f"✅ Generated query embedding: {len(query_embedding)} dimensions")
        
        # Test Milvus search
        milvus_service = get_milvus_service()
        search_results = milvus_service.search_similar(
            query_embedding=query_embedding,
            limit=5
        )
        
        print(f"✅ Vector search completed: {len(search_results)} results found")
        
        for i, result in enumerate(search_results[:3]):  # Show top 3
            print(f"   {i+1}. Score: {result['score']:.3f} - {result['url']}")
        
        return search_results
        
    except Exception as e:
        print(f"❌ Vector search test failed: {str(e)}")
        print("   This is likely due to missing API keys. Check your .env file.")
        return []


def test_database_stats():
    """Test database statistics."""
    print("📊 Checking database statistics...")
    
    # Django statistics
    scraped_pages = ScrapedPage.objects.count()
    summaries = PageSummary.objects.count()
    embeddings = DocumentEmbedding.objects.count()
    
    print(f"✅ Django database:")
    print(f"   Scraped pages: {scraped_pages}")
    print(f"   Summaries: {summaries}")
    print(f"   Embeddings: {embeddings}")
    
    # Milvus statistics
    try:
        milvus_service = get_milvus_service()
        milvus_stats = milvus_service.get_collection_stats()
        print(f"   Milvus entities: {milvus_stats['num_entities']}")
    except Exception as e:
        print(f"   Milvus stats error: {str(e)}")


def test_fastapi_endpoints():
    """Test FastAPI endpoints (if server is running)."""
    print("🌐 Testing FastAPI endpoints...")
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get('http://localhost:8001/health', timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI server is running")
            
            # Test search endpoint
            search_data = {
                "query": "test search query",
                "limit": 3
            }
            
            search_response = requests.post(
                'http://localhost:8001/search',
                json=search_data,
                timeout=10
            )
            
            if search_response.status_code == 200:
                results = search_response.json()
                print(f"✅ Search API working: {results['total_results']} results")
            else:
                print(f"⚠️  Search API error: {search_response.status_code}")
        else:
            print("❌ FastAPI server not responding")
            
    except requests.exceptions.RequestException:
        print("⚠️  FastAPI server not running or unreachable")
        print("   Start it with: python start_vector_api.py")


def main():
    """Run the complete test suite."""
    print("🎯 Vector Database System Test Suite")
    print("=" * 50)
    
    try:
        # Create test data
        domain, user = create_test_data()
        
        # Run scraping test
        job = run_scraping_test(domain)
        
        # Test manual summarization (if auto-summarization is disabled)
        if not getattr(django.conf.settings, 'ENABLE_AUTO_SUMMARIZATION', True):
            test_manual_summarization(job)
        
        # Test vector search
        test_vector_search()
        
        # Check database stats
        test_database_stats()
        
        # Test FastAPI endpoints
        test_fastapi_endpoints()
        
        print("\n🎉 Test suite completed!")
        print("\nNext steps:")
        print("1. Set up your API keys in .env file")
        print("2. Start the vector search API: python start_vector_api.py")
        print("3. Test the search functionality through the API")
        print("4. Monitor the Django admin interface for summaries and embeddings")
        
    except Exception as e:
        print(f"❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
