"""
APScheduler integration service for the scraping platform.
Handles job scheduling, execution, and monitoring with enterprise-grade features.
"""

import os
import json
import logging
import atexit
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from scraper.models import Domain, ScrapingJob
from scraper.services import ScrapingService, MetricsCollector

logger = logging.getLogger(__name__)


class ScrapingScheduler:
    """
    Enterprise-grade job scheduler for scraping operations.
    Integrates APScheduler with Django models.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.scheduler = None
        self.scraping_service = ScrapingService(use_dummy_api=True)
        self.setup_scheduler()
        self._initialized = True
    
    def setup_scheduler(self):
        """Initialize and configure the APScheduler."""
        
        config = settings.SCHEDULER_CONFIG
        
        # Configure job store
        jobstore = SQLAlchemyJobStore(url=config['DATABASE_URL'])
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(config['MAX_WORKERS'])
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': config.get('COALESCE', False),
            'max_instances': config.get('MAX_INSTANCES', 3),
            'misfire_grace_time': config.get('MISFIRE_GRACE_TIME', 30)
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores={'default': jobstore},
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._job_missed, EVENT_JOB_MISSED)
        
        logger.info("Scheduler configured successfully")
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Ensure scheduler shuts down when the app exits
            atexit.register(lambda: self.shutdown())
            
            # Schedule existing active domains
            self._schedule_existing_domains()
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down successfully")
    
    def _schedule_existing_domains(self):
        """Schedule jobs for all active domains on startup."""
        try:
            active_domains = Domain.objects.filter(status='active')
            for domain in active_domains:
                self.schedule_domain_scraping(domain)
            
            logger.info(f"Scheduled {active_domains.count()} existing domains")
        except Exception as e:
            logger.error(f"Error scheduling existing domains: {str(e)}")
    
    def schedule_domain_scraping(self, domain: Domain) -> str:
        """
        Schedule recurring scraping for a domain.
        Returns the job ID.
        """
        job_id = f"domain_scrape_{domain.id}"
        
        try:
            # Remove existing job if it exists
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass  # Job might not exist
            
            # Calculate next run time
            if domain.next_scrape and domain.next_scrape > timezone.now():
                next_run = domain.next_scrape
            else:
                next_run = timezone.now() + timedelta(minutes=1)  # Start soon
            
            # Schedule the job
            job = self.scheduler.add_job(
                self._execute_domain_scraping,
                'interval',
                hours=domain.scrape_frequency_hours,
                args=[domain.id],
                id=job_id,
                replace_existing=True,
                next_run_time=next_run,
                max_instances=1,
                name=f"Scrape {domain.name}"
            )
            
            # Update domain next scrape time
            domain.next_scrape = job.next_run_time
            domain.save(update_fields=['next_scrape'])
            
            logger.info(f"Scheduled domain scraping: {domain.name} (Job ID: {job_id})")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling domain {domain.name}: {str(e)}")
            raise
    
    def unschedule_domain_scraping(self, domain: Domain) -> bool:
        """
        Unschedule scraping for a domain.
        Returns True if successfully unscheduled.
        """
        job_id = f"domain_scrape_{domain.id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled domain scraping: {domain.name}")
            return True
        except:
            logger.warning(f"Job {job_id} not found for unscheduling")
            return False
    
    def schedule_immediate_scraping(self, domain: Domain) -> str:
        """
        Schedule immediate one-time scraping for a domain.
        Returns the job ID.
        """
        job_id = f"immediate_scrape_{domain.id}_{uuid.uuid4().hex[:8]}"
        
        try:
            job = self.scheduler.add_job(
                self._execute_domain_scraping,
                'date',
                args=[domain.id],
                id=job_id,
                run_date=timezone.now() + timedelta(seconds=5),
                name=f"Immediate scrape {domain.name}"
            )
            
            logger.info(f"Scheduled immediate scraping: {domain.name} (Job ID: {job_id})")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling immediate scraping for {domain.name}: {str(e)}")
            raise
    
    def _execute_domain_scraping(self, domain_id: str):
        """
        Execute scraping for a domain.
        This is the main job execution function called by APScheduler.
        """
        start_time = timezone.now()
        job = None
        
        try:
            logger.info(f"Starting scraping execution for domain ID: {domain_id}")
            
            # Get domain
            try:
                domain = Domain.objects.get(id=domain_id, status='active')
            except Domain.DoesNotExist:
                logger.warning(f"Domain {domain_id} not found or not active")
                return
            
            # Create scraping job record
            with transaction.atomic():
                job = ScrapingJob.objects.create(
                    domain=domain,
                    job_type='scheduled',
                    priority='medium',
                    status='pending',
                    scheduler_job_id=f"domain_scrape_{domain_id}"
                )
            
            logger.info(f"Created scraping job {job.id} for domain {domain.name}")
            
            # Execute scraping
            results = self.scraping_service.scrape_domain(domain, job)
            
            # Record metrics
            MetricsCollector.record_scraping_metrics(job)
            
            # Log completion
            duration = (timezone.now() - start_time).total_seconds()
            logger.info(
                f"Scraping completed for {domain.name}: "
                f"{results['summary']['successful_pages']} pages in {duration:.2f}s"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Scraping execution failed for domain {domain_id}: {str(e)}")
            
            # Update job with error if it exists
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = timezone.now()
                job.save()
            
            # Update domain failure count
            try:
                domain = Domain.objects.get(id=domain_id)
                domain.failed_scrapes += 1
                domain.save(update_fields=['failed_scrapes'])
            except:
                pass
            
            raise
    
    def _job_executed(self, event):
        """Handle successful job execution."""
        job_id = event.job_id
        logger.info(f"Job {job_id} executed successfully at {event.scheduled_run_time}")
    
    def _job_error(self, event):
        """Handle job execution errors."""
        job_id = event.job_id
        logger.error(f"Job {job_id} failed: {event.exception}")
        logger.error(f"Traceback: {event.traceback}")
    
    def _job_missed(self, event):
        """Handle missed job executions."""
        job_id = event.job_id
        logger.warning(f"Job {job_id} missed scheduled run time: {event.scheduled_run_time}")
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a scheduled job."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    'id': job.id,
                    'name': job.name,
                    'func': str(job.func),
                    'args': job.args,
                    'kwargs': job.kwargs,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'executor': job.executor,
                    'max_instances': job.max_instances,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting job info for {job_id}: {str(e)}")
            return None
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get information about all scheduled jobs."""
        try:
            jobs = self.scheduler.get_jobs()
            return [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                }
                for job in jobs
            ]
        except Exception as e:
            logger.error(f"Error getting all jobs: {str(e)}")
            return []
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {str(e)}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {str(e)}")
            return False
    
    def modify_job(self, job_id: str, **kwargs) -> bool:
        """Modify an existing job."""
        try:
            self.scheduler.modify_job(job_id, **kwargs)
            logger.info(f"Modified job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error modifying job {job_id}: {str(e)}")
            return False
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics."""
        try:
            return {
                'running': self.scheduler.running if self.scheduler else False,
                'total_jobs': len(self.scheduler.get_jobs()) if self.scheduler else 0,
                'job_stores': list(self.scheduler._jobstores.keys()) if self.scheduler else [],
                'executors': list(self.scheduler._executors.keys()) if self.scheduler else [],
                'timezone': str(self.scheduler.timezone) if self.scheduler else 'UTC',
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {str(e)}")
            return {'running': False, 'error': str(e)}


# Singleton instance
scheduler_service = ScrapingScheduler()


def get_scheduler() -> ScrapingScheduler:
    """Get the scheduler service instance."""
    return scheduler_service


# Django management utilities
class SchedulerManager:
    """Utility class for managing scheduler from Django management commands."""
    
    @staticmethod
    def start_scheduler():
        """Start the scheduler service."""
        scheduler = get_scheduler()
        scheduler.start()
        return scheduler
    
    @staticmethod
    def stop_scheduler():
        """Stop the scheduler service."""
        scheduler = get_scheduler()
        scheduler.shutdown()
    
    @staticmethod
    def restart_scheduler():
        """Restart the scheduler service."""
        scheduler = get_scheduler()
        scheduler.shutdown()
        scheduler.setup_scheduler()
        scheduler.start()
        return scheduler
    
    @staticmethod
    def sync_domain_schedules():
        """Synchronize all domain schedules with the scheduler."""
        scheduler = get_scheduler()
        
        # Get all active domains
        domains = Domain.objects.filter(status='active')
        
        # Remove orphaned jobs
        scheduled_jobs = scheduler.get_all_jobs()
        domain_job_ids = {f"domain_scrape_{d.id}" for d in domains}
        
        for job in scheduled_jobs:
            if job['id'].startswith('domain_scrape_') and job['id'] not in domain_job_ids:
                try:
                    scheduler.scheduler.remove_job(job['id'])
                    logger.info(f"Removed orphaned job: {job['id']}")
                except:
                    pass
        
        # Schedule all active domains
        for domain in domains:
            try:
                scheduler.schedule_domain_scraping(domain)
            except Exception as e:
                logger.error(f"Error scheduling domain {domain.name}: {str(e)}")
        
        logger.info(f"Synchronized {domains.count()} domain schedules")
