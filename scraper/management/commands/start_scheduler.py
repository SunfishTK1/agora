"""
Django management command to start the scheduler service.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging

from scheduler.scheduler_service import get_scheduler, SchedulerManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the scraping scheduler service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-domains',
            action='store_true',
            help='Synchronize all active domains with scheduler on startup',
        )
        
        parser.add_argument(
            '--workers',
            type=int,
            default=settings.SCHEDULER_CONFIG.get('MAX_WORKERS', 10),
            help='Number of worker threads for the scheduler',
        )
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS('Starting scraping scheduler...')
            )
            
            # Start the scheduler
            scheduler = SchedulerManager.start_scheduler()
            
            # Sync domains if requested
            if options['sync_domains']:
                self.stdout.write('Synchronizing domain schedules...')
                SchedulerManager.sync_domain_schedules()
                self.stdout.write(
                    self.style.SUCCESS('Domain schedules synchronized')
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Scheduler started successfully with {options["workers"]} workers'
                )
            )
            
            # Keep the command running
            self.stdout.write('Scheduler is running. Press Ctrl+C to stop.')
            
            try:
                # Keep the process alive
                import time
                while True:
                    time.sleep(10)
                    
                    # Check scheduler status
                    status = scheduler.get_scheduler_status()
                    if not status['running']:
                        self.stdout.write(
                            self.style.ERROR('Scheduler has stopped unexpectedly!')
                        )
                        break
                        
            except KeyboardInterrupt:
                self.stdout.write('\nShutting down scheduler...')
                scheduler.shutdown()
                self.stdout.write(
                    self.style.SUCCESS('Scheduler shut down successfully')
                )
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise CommandError(f'Failed to start scheduler: {str(e)}')
