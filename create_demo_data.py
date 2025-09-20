#!/usr/bin/env python
"""
Create demo data for testing the scraping platform.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
django.setup()

from scraper.models import Domain
from django.contrib.auth.models import User

def create_demo_data():
    """Create some demo domains for testing."""
    
    # Get or create a user
    user, created = User.objects.get_or_create(username='admin')
    
    # Create demo domains
    demo_domains = [
        {
            'name': 'Hacker News',
            'base_url': 'https://news.ycombinator.com/',
            'max_depth': 2,
            'max_pages': 50,
            'scrape_frequency_hours': 6,
            'status': 'active'
        },
        {
            'name': 'Reddit Programming',
            'base_url': 'https://reddit.com/r/programming/',
            'max_depth': 3,
            'max_pages': 100,
            'scrape_frequency_hours': 12,
            'status': 'active'
        },
        {
            'name': 'Dev.to Latest',
            'base_url': 'https://dev.to/latest',
            'max_depth': 2,
            'max_pages': 75,
            'scrape_frequency_hours': 8,
            'status': 'paused'
        }
    ]
    
    created_count = 0
    for domain_data in demo_domains:
        # Check if domain already exists
        if not Domain.objects.filter(name=domain_data['name']).exists():
            domain = Domain.objects.create(
                created_by=user,
                **domain_data
            )
            print(f"✅ Created domain: {domain.name}")
            created_count += 1
        else:
            print(f"⚠️  Domain already exists: {domain_data['name']}")
    
    print(f"\n🎉 Demo data creation complete! Created {created_count} new domains.")
    print("\n📊 Access your platform at:")
    print("   Dashboard: http://127.0.0.1:8002/dashboard/")
    print("   Domain List: http://127.0.0.1:8002/dashboard/domains/")
    print("   Add Domain: http://127.0.0.1:8002/dashboard/domains/create/")

if __name__ == '__main__':
    create_demo_data()
