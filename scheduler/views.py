"""
Views for scheduler management and monitoring.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .scheduler_service import get_scheduler, SchedulerManager


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def scheduler_status(request):
    """Display scheduler status and management interface."""
    
    scheduler = get_scheduler()
    status = scheduler.get_scheduler_status()
    jobs = scheduler.get_all_jobs()
    
    # Get recent job execution history from database
    from scraper.models import ScrapingJob
    recent_jobs = ScrapingJob.objects.select_related('domain').order_by('-created_at')[:20]
    
    context = {
        'status': status,
        'scheduled_jobs': jobs,
        'recent_jobs': recent_jobs,
    }
    
    return render(request, 'scheduler/status.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def start_scheduler(request):
    """Start the scheduler service."""
    try:
        scheduler = SchedulerManager.start_scheduler()
        messages.success(request, 'Scheduler started successfully!')
    except Exception as e:
        messages.error(request, f'Failed to start scheduler: {str(e)}')
    
    return redirect('scheduler:status')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def stop_scheduler(request):
    """Stop the scheduler service."""
    try:
        SchedulerManager.stop_scheduler()
        messages.success(request, 'Scheduler stopped successfully!')
    except Exception as e:
        messages.error(request, f'Failed to stop scheduler: {str(e)}')
    
    return redirect('scheduler:status')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def restart_scheduler(request):
    """Restart the scheduler service."""
    try:
        scheduler = SchedulerManager.restart_scheduler()
        messages.success(request, 'Scheduler restarted successfully!')
    except Exception as e:
        messages.error(request, f'Failed to restart scheduler: {str(e)}')
    
    return redirect('scheduler:status')


@login_required
@user_passes_test(is_staff_or_superuser)
def job_list(request):
    """List all scheduled jobs."""
    
    scheduler = get_scheduler()
    jobs = scheduler.get_all_jobs()
    
    context = {
        'jobs': jobs,
    }
    
    return render(request, 'scheduler/job_list.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def pause_job(request, job_id):
    """Pause a scheduled job."""
    try:
        scheduler = get_scheduler()
        if scheduler.pause_job(job_id):
            messages.success(request, f'Job {job_id} paused successfully!')
        else:
            messages.error(request, f'Failed to pause job {job_id}')
    except Exception as e:
        messages.error(request, f'Error pausing job: {str(e)}')
    
    return redirect('scheduler:status')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def resume_job(request, job_id):
    """Resume a paused job."""
    try:
        scheduler = get_scheduler()
        if scheduler.resume_job(job_id):
            messages.success(request, f'Job {job_id} resumed successfully!')
        else:
            messages.error(request, f'Failed to resume job {job_id}')
    except Exception as e:
        messages.error(request, f'Error resuming job: {str(e)}')
    
    return redirect('scheduler:status')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def delete_job(request, job_id):
    """Delete a scheduled job."""
    try:
        scheduler = get_scheduler()
        scheduler.scheduler.remove_job(job_id)
        messages.success(request, f'Job {job_id} deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting job: {str(e)}')
    
    return redirect('scheduler:status')


# API Views

@login_required
def api_scheduler_status(request):
    """API endpoint for scheduler status."""
    
    scheduler = get_scheduler()
    status = scheduler.get_scheduler_status()
    
    return JsonResponse(status)


@login_required
def api_job_list(request):
    """API endpoint for scheduled jobs list."""
    
    scheduler = get_scheduler()
    jobs = scheduler.get_all_jobs()
    
    return JsonResponse({
        'jobs': jobs,
        'count': len(jobs)
    })
