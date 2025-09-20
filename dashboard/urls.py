"""
URL patterns for the dashboard application.
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='home'),
    
    # Domain management
    path('domains/', views.domain_list, name='domain_list'),
    path('domains/create/', views.domain_create, name='domain_create'),
    path('domains/<uuid:domain_id>/', views.domain_detail, name='domain_detail'),
    path('domains/<uuid:domain_id>/edit/', views.domain_edit, name='domain_edit'),
    path('domains/<uuid:domain_id>/action/<str:action>/', views.domain_action, name='domain_action'),
    
    # Job monitoring
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='job_detail'),
    
    # Analytics and monitoring
    path('analytics/', views.analytics, name='analytics'),
    path('scheduler/', views.scheduler_status, name='scheduler_status'),
    path('enterprise/', views.data_engineer_console, name='data_engineer_console'),
    
    # API endpoints
    path('api/stats/', views.api_dashboard_stats, name='api_stats'),
    path('api/jobs/<uuid:job_id>/progress/', views.api_job_progress, name='api_job_progress'),
]
