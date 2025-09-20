"""
URL configuration for scraping_platform project.
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import RedirectView

# Import the remaining test view
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_recursive_crawler import test_recursive_crawler

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('scraper.urls')),
    path('scheduler/', include('scheduler.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('recursive/', test_recursive_crawler, name='recursive_crawler'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site configuration
admin.site.site_header = "Scraping Platform Administration"
admin.site.site_title = "Scraping Platform"
admin.site.index_title = "Welcome to Scraping Platform Administration"
