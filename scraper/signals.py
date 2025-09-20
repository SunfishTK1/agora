"""
Django signals for the scraper application.
Handles automatic scheduling and cleanup operations.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import logging

from .models import Domain, ScrapingJob
from scheduler.scheduler_service import get_scheduler

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Domain)
def handle_domain_save(sender, instance, created, **kwargs):
    """
    Handle domain creation and updates.
    Automatically schedule/unschedule domains based on status.
    """
    try:
        scheduler = get_scheduler()
        
        if created and instance.status == 'active':
            # New active domain - schedule it
            scheduler.schedule_domain_scraping(instance)
            logger.info(f"Automatically scheduled new domain: {instance.name}")
            
        elif not created:
            # Existing domain updated
            if instance.status == 'active':
                # Reschedule with updated parameters
                scheduler.unschedule_domain_scraping(instance)
                scheduler.schedule_domain_scraping(instance)
                logger.info(f"Rescheduled updated domain: {instance.name}")
                
            elif instance.status in ['paused', 'disabled', 'error']:
                # Remove from schedule
                scheduler.unschedule_domain_scraping(instance)
                logger.info(f"Unscheduled domain: {instance.name} (status: {instance.status})")
                
    except Exception as e:
        logger.error(f"Error handling domain signal for {instance.name}: {str(e)}")


@receiver(post_delete, sender=Domain)
def handle_domain_delete(sender, instance, **kwargs):
    """
    Handle domain deletion.
    Remove from scheduler when domain is deleted.
    """
    try:
        scheduler = get_scheduler()
        scheduler.unschedule_domain_scraping(instance)
        logger.info(f"Removed deleted domain from scheduler: {instance.name}")
        
    except Exception as e:
        logger.error(f"Error removing domain from scheduler: {str(e)}")


@receiver(post_save, sender=ScrapingJob)
def handle_job_save(sender, instance, created, **kwargs):
    """
    Handle scraping job updates.
    Update domain statistics when jobs complete.
    """
    if not created and instance.status in ['completed', 'failed']:
        try:
            # Update domain statistics
            domain = instance.domain
            
            # Recalculate totals
            jobs = domain.scraping_jobs.all()
            domain.total_scrapes = jobs.count()
            domain.successful_scrapes = jobs.filter(status='completed').count()
            domain.failed_scrapes = jobs.filter(status='failed').count()
            
            # Update next scrape time if this was a scheduled job
            if instance.job_type == 'scheduled' and instance.status == 'completed':
                domain.next_scrape = domain.get_next_scrape_time()
            
            domain.save(update_fields=[
                'total_scrapes', 'successful_scrapes', 'failed_scrapes', 'next_scrape'
            ])
            
            logger.info(f"Updated domain statistics for {domain.name}")
            
        except Exception as e:
            logger.error(f"Error updating domain statistics: {str(e)}")
