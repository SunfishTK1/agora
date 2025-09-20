"""
Dashboard views for the scraping platform.
Professional data engineer interface with real-time monitoring.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import timedelta

from scraper.models import Domain, ScrapingJob, ScrapedPage, SystemMetrics
from scheduler.scheduler_service import get_scheduler
from .forms import DomainForm, DomainConfigForm


@login_required
def dashboard_home(request):
    """Main dashboard with overview statistics."""
    
    # Get summary statistics
    total_domains = Domain.objects.count()
    active_domains = Domain.objects.filter(status='active').count()
    total_jobs = ScrapingJob.objects.count()
    running_jobs = ScrapingJob.objects.filter(status='running').count()
    
    # Recent activity
    recent_jobs = ScrapingJob.objects.select_related('domain').order_by('-created_at')[:10]
    
    # Performance metrics
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    jobs_today = ScrapingJob.objects.filter(created_at__date=today).count()
    jobs_yesterday = ScrapingJob.objects.filter(created_at__date=yesterday).count()
    
    pages_today = ScrapedPage.objects.filter(created_at__date=today).count()
    success_rate_today = 0
    
    if jobs_today > 0:
        successful_jobs_today = ScrapingJob.objects.filter(
            created_at__date=today,
            status='completed'
        ).count()
        success_rate_today = round((successful_jobs_today / jobs_today) * 100, 1)
    
    # Scheduler status
    scheduler = get_scheduler()
    scheduler_status = scheduler.get_scheduler_status()
    
    # Chart data for the last 7 days
    chart_data = []
    for i in range(7):
        date = today - timedelta(days=i)
        jobs_count = ScrapingJob.objects.filter(created_at__date=date).count()
        pages_count = ScrapedPage.objects.filter(created_at__date=date).count()
        chart_data.append({
            'date': date.strftime('%m/%d'),
            'jobs': jobs_count,
            'pages': pages_count
        })
    chart_data.reverse()
    
    context = {
        'total_domains': total_domains,
        'active_domains': active_domains,
        'total_jobs': total_jobs,
        'running_jobs': running_jobs,
        'recent_jobs': recent_jobs,
        'jobs_today': jobs_today,
        'jobs_yesterday': jobs_yesterday,
        'pages_today': pages_today,
        'success_rate_today': success_rate_today,
        'scheduler_status': scheduler_status,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def domain_list(request):
    """List all domains with filtering and search."""
    
    domains = Domain.objects.all()
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        domains = domains.filter(
            Q(name__icontains=search) |
            Q(domain__icontains=search) |
            Q(base_url__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        domains = domains.filter(status=status_filter)
    
    # Annotate with job counts
    domains = domains.annotate(
        job_count=Count('scraping_jobs'),
        recent_job_count=Count('scraping_jobs', filter=Q(scraping_jobs__created_at__gte=timezone.now() - timedelta(days=7)))
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(domains, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'status_choices': Domain.STATUS_CHOICES,
    }
    
    return render(request, 'dashboard/domain_list.html', context)


@login_required
def domain_create(request):
    """Create a new domain configuration."""
    
    if request.method == 'POST':
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.created_by = request.user
            domain.save()
            
            # Schedule the domain if it's active
            if domain.status == 'active':
                try:
                    scheduler = get_scheduler()
                    scheduler.schedule_domain_scraping(domain)
                    messages.success(request, f'Domain "{domain.name}" created and scheduled successfully!')
                except Exception as e:
                    messages.warning(request, f'Domain created but scheduling failed: {str(e)}')
            else:
                messages.success(request, f'Domain "{domain.name}" created successfully!')
            
            return redirect('dashboard:domain_list')
    else:
        form = DomainForm()
    
    context = {'form': form, 'title': 'Add New Domain'}
    return render(request, 'dashboard/domain_form.html', context)


@login_required
def domain_detail(request, domain_id):
    """Detailed view of a domain with jobs and statistics."""
    
    domain = get_object_or_404(Domain, id=domain_id)
    
    # Get recent jobs
    jobs = domain.scraping_jobs.order_by('-created_at')[:20]
    
    # Performance statistics
    last_30_days = timezone.now() - timedelta(days=30)
    recent_jobs = domain.scraping_jobs.filter(created_at__gte=last_30_days)
    
    stats = {
        'total_jobs': domain.scraping_jobs.count(),
        'recent_jobs': recent_jobs.count(),
        'avg_pages_per_job': recent_jobs.aggregate(Avg('pages_scraped'))['pages_scraped__avg'] or 0,
        'total_pages_scraped': recent_jobs.aggregate(Sum('pages_scraped'))['pages_scraped__sum'] or 0,
        'avg_job_duration': None
    }
    
    # Calculate average job duration
    completed_jobs = recent_jobs.filter(status='completed', started_at__isnull=False, completed_at__isnull=False)
    if completed_jobs.exists():
        durations = [(job.completed_at - job.started_at).total_seconds() for job in completed_jobs]
        stats['avg_job_duration'] = sum(durations) / len(durations)
    
    # Scheduler info
    scheduler = get_scheduler()
    job_id = f"domain_scrape_{domain.id}"
    scheduler_info = scheduler.get_job_info(job_id)
    
    context = {
        'domain': domain,
        'jobs': jobs,
        'stats': stats,
        'scheduler_info': scheduler_info,
    }
    
    return render(request, 'dashboard/domain_detail.html', context)


@login_required
def domain_edit(request, domain_id):
    """Edit domain configuration."""
    
    domain = get_object_or_404(Domain, id=domain_id)
    
    if request.method == 'POST':
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            old_status = domain.status
            domain = form.save()
            
            scheduler = get_scheduler()
            
            # Handle scheduling changes
            if domain.status == 'active' and old_status != 'active':
                try:
                    scheduler.schedule_domain_scraping(domain)
                    messages.success(request, 'Domain updated and scheduled successfully!')
                except Exception as e:
                    messages.warning(request, f'Domain updated but scheduling failed: {str(e)}')
            elif domain.status != 'active' and old_status == 'active':
                scheduler.unschedule_domain_scraping(domain)
                messages.success(request, 'Domain updated and unscheduled!')
            elif domain.status == 'active':
                # Reschedule with new parameters
                scheduler.unschedule_domain_scraping(domain)
                scheduler.schedule_domain_scraping(domain)
                messages.success(request, 'Domain updated and rescheduled!')
            else:
                messages.success(request, 'Domain updated successfully!')
            
            return redirect('dashboard:domain_detail', domain_id=domain.id)
    else:
        form = DomainForm(instance=domain)
    
    context = {'form': form, 'domain': domain, 'title': f'Edit {domain.name}'}
    return render(request, 'dashboard/domain_form.html', context)


@login_required
@require_http_methods(["POST"])
def domain_action(request, domain_id, action):
    """Handle domain actions (activate, pause, scrape_now, delete)."""
    
    domain = get_object_or_404(Domain, id=domain_id)
    scheduler = get_scheduler()
    
    if action == 'activate':
        domain.status = 'active'
        domain.save()
        try:
            scheduler.schedule_domain_scraping(domain)
            messages.success(request, f'Domain "{domain.name}" activated and scheduled!')
        except Exception as e:
            messages.error(request, f'Failed to schedule domain: {str(e)}')
    
    elif action == 'pause':
        domain.status = 'paused'
        domain.save()
        scheduler.unschedule_domain_scraping(domain)
        messages.success(request, f'Domain "{domain.name}" paused!')
    
    elif action == 'scrape_now':
        if domain.status == 'active':
            try:
                scheduler.schedule_immediate_scraping(domain)
                messages.success(request, f'Immediate scrape scheduled for "{domain.name}"!')
            except Exception as e:
                messages.error(request, f'Failed to schedule immediate scrape: {str(e)}')
        else:
            messages.error(request, 'Domain must be active to schedule scraping!')
    
    elif action == 'delete':
        domain_name = domain.name
        scheduler.unschedule_domain_scraping(domain)
        domain.delete()
        messages.success(request, f'Domain "{domain_name}" deleted successfully!')
        return redirect('dashboard:domain_list')
    
    return redirect('dashboard:domain_detail', domain_id=domain.id)


@login_required
def job_list(request):
    """List all scraping jobs with filtering."""
    
    jobs = ScrapingJob.objects.select_related('domain').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    
    # Filter by domain
    domain_filter = request.GET.get('domain')
    if domain_filter:
        jobs = jobs.filter(domain_id=domain_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        jobs = jobs.filter(
            Q(domain__name__icontains=search) |
            Q(domain__domain__icontains=search) |
            Q(id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(jobs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get domain choices for filter
    domains = Domain.objects.values('id', 'name').order_by('name')
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'domain_filter': domain_filter,
        'search': search,
        'status_choices': ScrapingJob.STATUS_CHOICES,
        'domains': domains,
    }
    
    return render(request, 'dashboard/job_list.html', context)


@login_required
def job_detail(request, job_id):
    """Detailed view of a scraping job."""
    
    job = get_object_or_404(ScrapingJob, id=job_id)
    
    # Get scraped pages
    pages = job.scraped_pages.order_by('-created_at')
    
    # Pagination for pages
    paginator = Paginator(pages, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_pages': pages.count(),
        'successful_pages': pages.filter(status='success').count(),
        'failed_pages': pages.filter(status='failed').count(),
        'avg_processing_time': pages.filter(processing_time_ms__isnull=False).aggregate(
            Avg('processing_time_ms')
        )['processing_time_ms__avg'] or 0,
    }
    
    context = {
        'job': job,
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'dashboard/job_detail.html', context)


@login_required
def analytics(request):
    """Analytics dashboard with charts and metrics."""
    
    # Time range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Job statistics
    jobs = ScrapingJob.objects.filter(created_at__gte=start_date)
    job_stats = {
        'total': jobs.count(),
        'completed': jobs.filter(status='completed').count(),
        'failed': jobs.filter(status='failed').count(),
        'running': jobs.filter(status='running').count(),
    }
    
    # Page statistics
    pages = ScrapedPage.objects.filter(created_at__gte=start_date)
    page_stats = {
        'total': pages.count(),
        'successful': pages.filter(status='success').count(),
        'failed': pages.filter(status='failed').count(),
    }
    
    # Daily activity data
    daily_data = []
    for i in range(days):
        date = timezone.now().date() - timedelta(days=i)
        day_jobs = ScrapingJob.objects.filter(created_at__date=date)
        day_pages = ScrapedPage.objects.filter(created_at__date=date)
        
        daily_data.append({
            'date': date.strftime('%m/%d'),
            'jobs': day_jobs.count(),
            'pages': day_pages.count(),
            'success_rate': (day_pages.filter(status='success').count() / max(day_pages.count(), 1)) * 100
        })
    
    daily_data.reverse()
    
    # Top performing domains
    top_domains = Domain.objects.annotate(
        recent_jobs=Count('scraping_jobs', filter=Q(scraping_jobs__created_at__gte=start_date)),
        recent_pages=Sum('scraping_jobs__pages_scraped', filter=Q(scraping_jobs__created_at__gte=start_date))
    ).filter(recent_jobs__gt=0).order_by('-recent_pages')[:10]
    
    # System metrics
    metrics = SystemMetrics.objects.filter(created_at__gte=start_date).values(
        'metric_name'
    ).annotate(
        avg_value=Avg('metric_value'),
        count=Count('id')
    ).order_by('metric_name')
    
    context = {
        'days': days,
        'job_stats': job_stats,
        'page_stats': page_stats,
        'daily_data': json.dumps(daily_data),
        'top_domains': top_domains,
        'metrics': metrics,
    }
    
    return render(request, 'dashboard/analytics.html', context)


@login_required
def scheduler_status(request):
    """Scheduler status and management page."""
    
    scheduler = get_scheduler()
    status = scheduler.get_scheduler_status()
    jobs = scheduler.get_all_jobs()
    
    context = {
        'status': status,
        'jobs': jobs,
    }
    
    return render(request, 'dashboard/scheduler_status.html', context)


# API endpoints for AJAX requests
@login_required
def api_dashboard_stats(request):
    """API endpoint for real-time dashboard statistics."""
    
    stats = {
        'total_domains': Domain.objects.count(),
        'active_domains': Domain.objects.filter(status='active').count(),
        'running_jobs': ScrapingJob.objects.filter(status='running').count(),
        'scheduler_running': get_scheduler().get_scheduler_status()['running'],
        'timestamp': timezone.now().isoformat(),
    }
    
    return JsonResponse(stats)


@login_required
def api_job_progress(request, job_id):
    """API endpoint for job progress information."""
    
    try:
        job = ScrapingJob.objects.get(id=job_id)
        
        data = {
            'id': str(job.id),
            'status': job.status,
            'pages_scraped': job.pages_scraped,
            'pages_failed': job.pages_failed,
            'duration': None,
            'success_rate': job.success_rate,
        }
        
        if job.duration:
            data['duration'] = int(job.duration.total_seconds())
        
        return JsonResponse(data)
    
    except ScrapingJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
