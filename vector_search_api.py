"""
FastAPI service for querying the vector database.
Provides REST endpoints for semantic search and document retrieval.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from scraper.ai_services import AzureOpenAIEmbeddingService
from scraper.milvus_service import get_milvus_service
from scraper.summarization_pipeline import SummarizationPipeline

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Vector Search API",
    description="Semantic search API for document embeddings",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
embedding_service = AzureOpenAIEmbeddingService()
milvus_service = get_milvus_service()
pipeline = SummarizationPipeline()


# Pydantic models
class SearchQuery(BaseModel):
    """Search query model."""
    query: str = Field(..., min_length=1, max_length=10000, description="Search query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    domain: Optional[str] = Field(None, description="Filter results by domain")
    threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")


class SearchResult(BaseModel):
    """Individual search result."""
    id: str
    score: float
    url: str
    domain: str
    summary_id: str
    created_at: str
    content_snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: float
    domain_filter: Optional[str] = None


class DocumentInfo(BaseModel):
    """Document information model."""
    summary_id: str
    url: str
    domain: str
    created_at: str
    summary_text: Optional[str] = None


class StatsResponse(BaseModel):
    """Statistics response model."""
    django_summaries: int
    django_embeddings: int
    milvus_entities: int
    file_stats: Dict[str, Any]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/search", response_model=SearchResponse)
async def search_documents(search_query: SearchQuery):
    """
    Search for similar documents using semantic similarity.

    This endpoint:
    1. Converts the query text to an embedding
    2. Searches the Milvus vector database
    3. Returns the most similar documents with metadata
    """
    start_time = time.time()

    try:
        # Generate embedding for query
        logger.info(f"Processing search query: {search_query.query[:100]}...")
        query_embedding = embedding_service.generate_embedding(search_query.query)

        # Search Milvus database
        search_results = milvus_service.search_similar(
            query_embedding=query_embedding,
            limit=search_query.limit,
            domain_filter=search_query.domain
        )

        # Format results
        results = []
        for result in search_results:
            # Get summary content from Django if needed
            content_snippet = None
            try:
                from scraper.models import PageSummary
                summary = PageSummary.objects.get(id=result['summary_id'])
                content_snippet = summary.summary_text[:200] + "..." if len(summary.summary_text) > 200 else summary.summary_text
            except:
                pass

            results.append(SearchResult(
                id=result['id'],
                score=result['score'],
                url=result['url'],
                domain=result['domain'],
                summary_id=result['summary_id'],
                created_at=result['created_at'],
                content_snippet=content_snippet
            ))

        processing_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=search_query.query,
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time,
            domain_filter=search_query.domain
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/document/{summary_id}")
async def get_document(summary_id: str):
    """
    Get detailed information about a specific document.

    Args:
        summary_id: ID of the summary to retrieve
    """
    try:
        from scraper.models import PageSummary, ScrapedPage

        # Get summary
        summary = PageSummary.objects.get(id=summary_id)

        # Get associated scraped page
        scraped_page = summary.scraped_page

        # Get embeddings count
        embeddings_count = summary.embeddings.count()

        return DocumentInfo(
            summary_id=str(summary.id),
            url=scraped_page.url,
            domain=scraped_page.job.domain.domain,
            created_at=summary.created_at.isoformat(),
            summary_text=summary.summary_text
        )

    except PageSummary.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error retrieving document {summary_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")


@app.post("/reindex")
async def trigger_reindex(background_tasks: BackgroundTasks):
    """
    Trigger reindexing of documents in the background.

    This endpoint starts a background task to process any pages
    that haven't been summarized and embedded yet.
    """
    try:
        # Start background processing
        background_tasks.add_task(pipeline.process_scraped_pages)

        return {
            "message": "Reindexing started in background",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting reindex: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start reindex: {str(e)}")


@app.post("/reindex/domain/{domain}")
async def reindex_domain(domain: str, background_tasks: BackgroundTasks):
    """
    Trigger reindexing for a specific domain.

    Args:
        domain: Domain to reindex
    """
    try:
        # Start background processing for specific domain
        background_tasks.add_task(pipeline.process_scraped_pages, None, domain)

        return {
            "message": f"Reindexing started for domain {domain}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting domain reindex for {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start domain reindex: {str(e)}")


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get statistics about the vector database and processing pipeline.
    """
    try:
        stats = pipeline.get_pipeline_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.delete("/domain/{domain}")
async def delete_domain_data(domain: str):
    """
    Delete all data for a specific domain.

    Args:
        domain: Domain to delete data for
    """
    try:
        # Delete from Milvus
        deleted_count = milvus_service.delete_by_domain(domain)

        # Delete from Django (this will cascade)
        from scraper.models import PageSummary, DocumentEmbedding
        from django.db import transaction

        with transaction.atomic():
            summaries_deleted = PageSummary.objects.filter(
                scraped_page__job__domain__domain=domain
            ).delete()[0]

            embeddings_deleted = DocumentEmbedding.objects.filter(
                summary__scraped_page__job__domain__domain=domain
            ).delete()[0]

        return {
            "message": f"Deleted data for domain {domain}",
            "milvus_deleted": deleted_count,
            "summaries_deleted": summaries_deleted,
            "embeddings_deleted": embeddings_deleted,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error deleting domain {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete domain data: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Vector Search API",
        "version": "1.0.0",
        "description": "Semantic search API for document embeddings",
        "endpoints": {
            "/health": "Health check",
            "/search": "Search documents",
            "/document/{id}": "Get document details",
            "/reindex": "Trigger reindexing",
            "/stats": "Get statistics"
        }
    }


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the FastAPI server."""
    logger.info(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
