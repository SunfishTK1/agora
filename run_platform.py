#!/usr/bin/env python
"""
Startup script for the Scraping Platform.
Handles database migration, static files, and service startup.
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraping_platform.settings')

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        return False

def setup_django():
    """Setup Django environment."""
    print("🚀 Setting up Django environment...")
    
    # Check if manage.py exists
    if not (BASE_DIR / 'manage.py').exists():
        print("❌ manage.py not found. Make sure you're in the project root directory.")
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
        
    if not run_command("python manage.py migrate", "Applying database migrations"):
        return False
    
    # Collect static files
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        return False
    
    # Create superuser if it doesn't exist
    create_superuser_script = """
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
"""
    
    print("🔄 Creating default superuser...")
    result = subprocess.run([
        sys.executable, 'manage.py', 'shell', '-c', create_superuser_script
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Superuser setup completed")
        print(result.stdout)
    else:
        print("⚠️  Superuser setup failed (may already exist)")
    
    return True

def start_django_server():
    """Start Django development server."""
    print("🌐 Starting Django development server...")
    try:
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Django server stopped")

def start_scheduler():
    """Start the scheduler in a separate thread."""
    def scheduler_thread():
        print("⏰ Starting scheduler service...")
        time.sleep(5)  # Wait for Django to start
        try:
            subprocess.run([
                sys.executable, 'manage.py', 'start_scheduler', '--sync-domains'
            ])
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped")
    
    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
    return thread

def main():
    """Main entry point."""
    print("=" * 60)
    print("🔥 ENTERPRISE SCRAPING PLATFORM STARTUP 🔥")
    print("=" * 60)
    
    # Setup Django
    if not setup_django():
        print("❌ Failed to setup Django environment")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎯 PLATFORM READY - STARTING SERVICES")
    print("=" * 60)
    
    # Start scheduler in background
    scheduler_thread = start_scheduler()
    
    print("\n📊 Access the platform:")
    print("   Dashboard: http://localhost:8000/dashboard/")
    print("   Admin:     http://localhost:8000/admin/")
    print("   API Docs:  http://localhost:8000/api/docs/")
    print("   API Root:  http://localhost:8000/api/")
    print("\n🔐 Default superuser: admin / admin123")
    print("\n💡 Press Ctrl+C to stop all services")
    print("=" * 60)
    
    # Start Django server (blocking)
    try:
        start_django_server()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down platform...")
        print("✅ Platform stopped successfully")

if __name__ == '__main__':
    main()
