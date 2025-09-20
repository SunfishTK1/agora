#!/usr/bin/env python
"""
🚀 Nova Web Scraping Platform - Complete Integration Startup
Enterprise-grade platform with Agora Crawler & Vector Database integration
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

# Setup environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')
os.environ.setdefault('ENABLE_AUTO_SUMMARIZATION', 'False')  # Disable by default

def print_banner():
    """Print startup banner."""
    banner = """
🌟 ============================================================ 🌟
   🚀 NOVA WEB SCRAPING PLATFORM - PRODUCTION READY 🚀
🌟 ============================================================ 🌟

📋 ENTERPRISE FEATURES INCLUDED:
   ✅ Agora Crawler with Robots.txt Compliance
   ✅ Recursive Crawling with Domain Boundaries  
   ✅ Professional Django Dashboard
   ✅ REST API with DRF Integration
   ✅ APScheduler Job Management
   ✅ Vector Database Backend (Optional)
   ✅ AI Summarization Pipeline (Optional)

🔧 TECHNICAL STACK:
   • Django 4.2 + REST Framework
   • APScheduler for Background Jobs
   • Bootstrap Dashboard UI
   • Enterprise Database Models
   • Production-Ready Architecture

🌐 AVAILABLE ENDPOINTS:
   • http://127.0.0.1:8001/ - Main Platform
   • http://127.0.0.1:8001/dashboard/ - Web Dashboard
   • http://127.0.0.1:8001/api/ - REST API
   • http://127.0.0.1:8001/admin/ - Django Admin
   • http://127.0.0.1:8001/test-agora/ - Agora Crawler Test
   • http://127.0.0.1:8001/recursive/ - Recursive Crawler Test

🌟 ============================================================ 🌟
"""
    print(banner)

def setup_django():
    """Setup Django environment."""
    try:
        import django
        django.setup()
        print("✅ Django environment initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False

def check_database():
    """Check if database is properly migrated."""
    try:
        from django.core.management import execute_from_command_line
        print("🔍 Checking database migrations...")
        
        # Run migrations silently
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=0'])
        print("✅ Database migrations completed")
        return True
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def test_agora_crawler():
    """Test agora crawler functionality."""
    try:
        from scraper.agora_crawler import get_agora_crawler_service
        crawler = get_agora_crawler_service()
        print("✅ Agora Crawler initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Agora Crawler test failed: {e}")
        return False

def create_superuser_if_needed():
    """Create a superuser if none exists."""
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print("👤 Creating default superuser (admin/admin)...")
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin'
            )
            print("✅ Superuser created: admin/admin")
        else:
            print("✅ Superuser already exists")
        return True
    except Exception as e:
        print(f"❌ Superuser creation failed: {e}")
        return False

def start_server():
    """Start the Django development server."""
    try:
        print("\n🚀 Starting Nova Platform Server...")
        print("📍 Server will be available at: http://127.0.0.1:8001")
        print("🎯 Dashboard at: http://127.0.0.1:8001/dashboard/")
        print("🔧 Admin at: http://127.0.0.1:8001/admin/")
        print("🧪 Agora Test at: http://127.0.0.1:8001/test-agora/")
        print("\n⚡ Press Ctrl+C to stop the server")
        print("=" * 60)
        
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8001'])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")

def main():
    """Main startup function."""
    print_banner()
    
    # Setup checks
    checks_passed = True
    
    if not setup_django():
        checks_passed = False
    
    if not check_database():
        checks_passed = False
    
    if not test_agora_crawler():
        checks_passed = False
    
    if not create_superuser_if_needed():
        checks_passed = False
    
    if not checks_passed:
        print("\n❌ Some initialization checks failed. Please review the errors above.")
        sys.exit(1)
    
    print("\n✅ ALL SYSTEMS READY!")
    time.sleep(1)
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()
