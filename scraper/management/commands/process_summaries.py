"""
Django management command to process scraped pages into summaries and embeddings.
"""

import logging
from typing import Optional
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scraper.summarization_pipeline import SummarizationPipeline, BatchSummarizationService
from scraper.models import Domain, ScrapedPage, PageSummary

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process scraped pages to generate summaries and embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            help='Process pages for a specific domain only'
        )
        parser.add_argument(
            '--job-id',
            type=str,
            help='Process pages for a specific job ID only'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of pages to process in each batch (default: 10)'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            help='Maximum number of pages to process'
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess pages that already have summaries'
        )
        parser.add_argument(
            '--all-domains',
            action='store_true',
            help='Process all active domains'
        )

    def handle(self, *args, **options):
        """Execute the summarization command."""
        domain = options.get('domain')
        job_id = options.get('job_id')
        batch_size = options.get('batch_size', 10)
        max_pages = options.get('max_pages')
        reprocess = options.get('reprocess', False)
        all_domains = options.get('all_domains', False)

        self.stdout.write(
            self.style.SUCCESS('Starting summarization and embedding pipeline...')
        )

        try:
            if all_domains:
                # Process all domains
                batch_service = BatchSummarizationService()
                stats = batch_service.process_all_domains()

                self.stdout.write(
                    self.style.SUCCESS(f"Processed {stats['processed_domains']} domains")
                )
                self.stdout.write(
                    f"Total pages processed: {stats['total_pages_processed']}"
                )
                self.stdout.write(
                    f"Total summaries created: {stats['total_summaries_created']}"
                )
                self.stdout.write(
                    f"Total embeddings created: {stats['total_embeddings_created']}"
                )

            elif domain:
                # Process specific domain
                batch_service = BatchSummarizationService()
                stats = batch_service.process_domain_batch(domain, max_pages)

                self.stdout.write(
                    self.style.SUCCESS(f"Processed domain: {domain}")
                )
                self._print_stats(stats)

            else:
                # Process with general parameters
                pipeline = SummarizationPipeline()

                if reprocess:
                    # Reprocess failed pages
                    stats = pipeline.reprocess_failed_pages(domain, max_pages or 100)
                    self.stdout.write(
                        self.style.SUCCESS(f"Reprocessed pages: {stats}")
                    )
                else:
                    # Normal processing
                    stats = pipeline.process_scraped_pages(
                        job_id=job_id,
                        domain=domain,
                        batch_size=batch_size
                    )
                    self._print_stats(stats)

        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            raise CommandError(f'Summarization failed: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS('Summarization pipeline completed successfully!')
        )

    def _print_stats(self, stats: dict):
        """Print processing statistics."""
        if 'error' in stats:
            self.stdout.write(
                self.style.ERROR(f"Error: {stats['error']}")
            )
            return

        self.stdout.write(f"Total pages: {stats.get('total_pages', 0)}")
        self.stdout.write(f"Processed pages: {stats.get('processed_pages', 0)}")
        self.stdout.write(f"Successful summaries: {stats.get('successful_summaries', 0)}")
        self.stdout.write(f"Successful embeddings: {stats.get('successful_embeddings', 0)}")
        self.stdout.write(f"Failed pages: {stats.get('failed_pages', 0)}")
        
        processing_time = stats.get('total_processing_time', 0)
        avg_time = stats.get('average_time_per_page', 0)
        
        self.stdout.write(f"Total processing time: {processing_time:.2f}s")
        self.stdout.write(f"Average time per page: {avg_time:.2f}s")
