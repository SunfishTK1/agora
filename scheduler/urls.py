"""
URL patterns for the scheduler application.
"""

from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    # Scheduler management
    path('status/', views.scheduler_status, name='status'),
    path('start/', views.start_scheduler, name='start'),
    path('stop/', views.stop_scheduler, name='stop'),
    path('restart/', views.restart_scheduler, name='restart'),
    
    # Job management
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<str:job_id>/pause/', views.pause_job, name='pause_job'),
    path('jobs/<str:job_id>/resume/', views.resume_job, name='resume_job'),
    path('jobs/<str:job_id>/delete/', views.delete_job, name='delete_job'),
    
    # API endpoints
    path('api/status/', views.api_scheduler_status, name='api_status'),
    path('api/jobs/', views.api_job_list, name='api_jobs'),
]
