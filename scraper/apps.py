"""
Django app configuration for the scraper application.
"""

from django.apps import AppConfig


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'
    verbose_name = 'Web Scraper'
    
    def ready(self):
        """Called when the app is ready."""
        # Import signal handlers
        try:
            from . import signals
        except ImportError:
            pass
