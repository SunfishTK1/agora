"""
Summarization and embedding pipeline service.
Orchestrates the complete process from scraped pages to vector embeddings.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.db import transaction
from .models import ScrapedPage, PageSummary, DocumentEmbedding
from .ai_services import AzureOpenAIService, AzureOpenAIEmbeddingService
from .file_organization import FileOrganizationService
from .milvus_service import get_milvus_service

logger = logging.getLogger(__name__)


class SummarizationPipeline:
    """
    Complete pipeline for processing scraped pages into summaries and embeddings.
    Handles batch processing, error recovery, and performance optimization.
    """

    def __init__(self):
        self.azure_service = AzureOpenAIService()
        self.embedding_service = AzureOpenAIEmbeddingService()
        self.file_service = FileOrganizationService()
        self.milvus_service = get_milvus_service()

    def process_scraped_pages(self, job_id: str = None, domain: str = None,
                             batch_size: int = 10) -> Dict[str, Any]:
        """
        Process scraped pages to generate summaries and embeddings.

        Args:
            job_id: Optional job ID to process pages from
            domain: Optional domain filter
            batch_size: Number of pages to process in each batch

        Returns:
            Processing statistics
        """
        start_time = time.time()

        try:
            # Get pages to process
            queryset = ScrapedPage.objects.filter(
                status='success'
            ).exclude(
                summary__isnull=False  # Already processed
            )

            if job_id:
                queryset = queryset.filter(job_id=job_id)
            if domain:
                queryset = queryset.filter(
                    job__domain__domain=domain
                )

            total_pages = queryset.count()

            if total_pages == 0:
                return {
                    'status': 'no_pages',
                    'message': 'No pages to process',
                    'total_pages': 0
                }

            logger.info(f"Starting summarization pipeline for {total_pages} pages")

            stats = {
                'total_pages': total_pages,
                'processed_pages': 0,
                'successful_summaries': 0,
                'successful_embeddings': 0,
                'failed_pages': 0,
                'total_processing_time': 0
            }

            # Process in batches for memory efficiency
            processed_count = 0
            for page in queryset.iterator(chunk_size=batch_size):
                try:
                    page_start_time = time.time()

                    # Process single page
                    result = self._process_single_page(page)

                    if result['summary_created']:
                        stats['successful_summaries'] += 1

                    if result['embedding_created']:
                        stats['successful_embeddings'] += 1

                    stats['processed_pages'] += 1
                    processed_count += 1

                    page_processing_time = time.time() - page_start_time
                    logger.info(f"Processed page {processed_count}/{total_pages} "
                              f"({page_processing_time:.2f}s)")

                except Exception as e:
                    logger.error(f"Error processing page {page.id}: {str(e)}")
                    stats['failed_pages'] += 1
                    continue

            # Final statistics
            stats['total_processing_time'] = time.time() - start_time
            stats['average_time_per_page'] = stats['total_processing_time'] / max(stats['processed_pages'], 1)

            logger.info(f"Pipeline completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'total_pages': 0
            }

    def _process_single_page(self, page: ScrapedPage) -> Dict[str, Any]:
        """
        Process a single scraped page through the complete pipeline.

        Returns:
            Dictionary with processing results
        """
        result = {
            'summary_created': False,
            'embedding_created': False,
            'file_path': '',
            'errors': []
        }

        try:
            # Generate summary
            summary_data = self.azure_service.generate_summary(
                text=page.content,
                url=page.url,
                title=page.title
            )

            # Organize summary file
            file_path = self.file_service.organize_summary(
                summary_data, page.url
            )
            summary_data['file_path'] = file_path

            # Save summary to database
            with transaction.atomic():
                summary = PageSummary.objects.create(
                    scraped_page=page,
                    summary_text=summary_data['summary_text'],
                    summary_length_tokens=summary_data['summary_length_tokens'],
                    processing_time_ms=summary_data['processing_time_ms'],
                    model_used=summary_data['model_used'],
                    chunk_count=summary_data['chunk_count'],
                    compression_ratio=summary_data['compression_ratio'],
                    file_path=file_path
                )

                result['summary_created'] = True

                # Generate embedding
                embedding_vector = self.embedding_service.generate_embedding(
                    summary_data['summary_text']
                )

                # Create embedding ID
                embedding_id = f"{page.job.domain.domain}_{page.id}_{int(time.time())}"

                # Prepare Milvus data
                milvus_data = {
                    'embedding_id': embedding_id,
                    'embedding_vector': embedding_vector,
                    'summary_id': str(summary.id),
                    'url': page.url,
                    'domain': page.job.domain.domain,
                    'created_at': datetime.now().isoformat()
                }

                # Insert into Milvus
                self.milvus_service.insert_embedding(milvus_data)

                # Save embedding reference to Django
                DocumentEmbedding.objects.create(
                    summary=summary,
                    embedding_id=embedding_id,
                    embedding_vector=embedding_vector,
                    model_used='text-embedding-large-3',
                    vector_dimensions=len(embedding_vector),
                    processing_time_ms=int((time.time() - time.time()) * 1000)  # Simplified
                )

                result['embedding_created'] = True
                result['file_path'] = file_path

            logger.info(f"Successfully processed page {page.url}")
            return result

        except Exception as e:
            error_msg = f"Error processing page {page.url}: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result

    def reprocess_failed_pages(self, domain: str = None, limit: int = 100) -> Dict[str, Any]:
        """
        Reprocess pages that failed during previous attempts.

        Args:
            domain: Optional domain filter
            limit: Maximum number of pages to reprocess

        Returns:
            Processing statistics for reprocessing
        """
        try:
            # Find pages with summaries that have errors or incomplete data
            queryset = PageSummary.objects.filter(
                information_density_score=0.0  # Placeholder for failed processing
            )

            if domain:
                queryset = queryset.filter(scraped_page__job__domain__domain=domain)

            queryset = queryset[:limit]

            stats = {
                'pages_to_reprocess': queryset.count(),
                'successful_reprocessing': 0,
                'failed_reprocessing': 0
            }

            for summary in queryset:
                try:
                    # Delete existing failed summary
                    summary.delete()

                    # Reprocess the page
                    result = self._process_single_page(summary.scraped_page)

                    if result['summary_created'] and result['embedding_created']:
                        stats['successful_reprocessing'] += 1
                    else:
                        stats['failed_reprocessing'] += 1

                except Exception as e:
                    logger.error(f"Error reprocessing page {summary.scraped_page.url}: {str(e)}")
                    stats['failed_reprocessing'] += 1

            return stats

        except Exception as e:
            logger.error(f"Error in reprocessing: {str(e)}")
            return {'error': str(e)}

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get overall statistics about the summarization pipeline."""
        try:
            summary_count = PageSummary.objects.count()
            embedding_count = DocumentEmbedding.objects.count()

            # Get Milvus stats
            milvus_stats = self.milvus_service.get_collection_stats()

            return {
                'django_summaries': summary_count,
                'django_embeddings': embedding_count,
                'milvus_entities': milvus_stats.get('num_entities', 0),
                'file_stats': self.file_service.get_file_stats()
            }

        except Exception as e:
            logger.error(f"Error getting pipeline stats: {str(e)}")
            return {'error': str(e)}


class BatchSummarizationService:
    """
    Service for batch processing of large numbers of pages.
    Optimized for high-throughput processing with resource management.
    """

    def __init__(self, max_concurrent_jobs: int = 5):
        self.pipeline = SummarizationPipeline()
        self.max_concurrent_jobs = max_concurrent_jobs

    def process_domain_batch(self, domain: str, max_pages: int = None) -> Dict[str, Any]:
        """
        Process all pages for a specific domain.

        Args:
            domain: Domain to process
            max_pages: Maximum number of pages to process (None for all)

        Returns:
            Batch processing statistics
        """
        logger.info(f"Starting batch processing for domain: {domain}")

        result = self.pipeline.process_scraped_pages(domain=domain, batch_size=20)

        if max_pages and result.get('processed_pages', 0) >= max_pages:
            result['status'] = 'max_pages_reached'

        return result

    def process_all_domains(self, domains: List[str] = None) -> Dict[str, Any]:
        """
        Process all domains or a specified list of domains.

        Args:
            domains: List of domains to process (None for all)

        Returns:
            Overall batch processing statistics
        """
        from .models import Domain

        # Get domains to process
        queryset = Domain.objects.filter(status='active')

        if domains:
            queryset = queryset.filter(domain__in=domains)

        total_stats = {
            'total_domains': 0,
            'processed_domains': 0,
            'total_pages_processed': 0,
            'total_summaries_created': 0,
            'total_embeddings_created': 0,
            'domain_results': []
        }

        for domain_obj in queryset:
            total_stats['total_domains'] += 1

            try:
                domain_result = self.process_domain_batch(domain_obj.domain)
                total_stats['processed_domains'] += 1
                total_stats['total_pages_processed'] += domain_result.get('processed_pages', 0)
                total_stats['total_summaries_created'] += domain_result.get('successful_summaries', 0)
                total_stats['total_embeddings_created'] += domain_result.get('successful_embeddings', 0)

                total_stats['domain_results'].append({
                    'domain': domain_obj.domain,
                    'result': domain_result
                })

            except Exception as e:
                logger.error(f"Error processing domain {domain_obj.domain}: {str(e)}")
                total_stats['domain_results'].append({
                    'domain': domain_obj.domain,
                    'error': str(e)
                })

        return total_stats
