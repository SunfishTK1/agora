# Vector Database Backend Integration

This document describes the vector database backend integration that adds AI-powered summarization and semantic search capabilities to the existing web scraping platform.

## Architecture Overview

The system consists of several integrated components:

1. **Azure OpenAI Integration**: GPT-5 chat for intelligent text summarization
2. **Azure OpenAI Embeddings**: text-embedding-large-3 for vector generation (with OpenAI fallback)
3. **Milvus Lite**: Vector database for storing and querying embeddings
4. **FastAPI Service**: REST API for semantic search queries
5. **Django Integration**: Seamless integration with existing scraping workflow

## Key Features

### Intelligent Summarization
- **Dense Summaries**: AI-generated summaries optimized for information density
- **Smart Chunking**: Automatic text chunking for documents >120k tokens
- **High Throughput**: Designed for 15M TPM and 100k RPM limits
- **Quality Metrics**: Compression ratios and information density scoring

### Vector Storage & Search
- **Milvus Lite**: Local vector database with minimal metadata overhead
- **Efficient Schema**: Optimized for high-performance similarity search
- **Batch Processing**: Support for large-scale embedding operations
- **Domain Filtering**: Search within specific domains or across all data

### File Organization
- **Structured Storage**: Domain/subpath directory hierarchy
- **Content Preservation**: Original HTML, extracted text, and metadata
- **Summary Storage**: Organized summary files with same path structure
- **Dynamic Domains**: Support for subdomains and complex URL structures

## Installation & Setup

### 1. Install Dependencies

The required packages have been added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Update your `.env` file with the following settings:

```bash
# Azure OpenAI Configuration (for GPT-5 summarization - separate deployment)
AZURE_OPENAI_API_KEY=your-gpt-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-gpt-resource.openai.azure.com/
AZURE_OPENAI_MODEL=gpt-5-chat
AZURE_OPENAI_EMBEDDING_API_KEY=your-embedding-azure-openai-api-key
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-embedding-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-large-3

# OpenAI Configuration (fallback for embeddings if Azure not available)
OPENAI_API_KEY=your-openai-api-key

# Vector Database Configuration
MILVUS_DB_PATH=./milvus_lite.db
SCRAPED_DATA_DIR=./scraped_data

# Summarization Settings
ENABLE_AUTO_SUMMARIZATION=True
MAX_CONTEXT_TOKENS=120000
MAX_OUTPUT_TOKENS=8000

# Vector Search API Settings
VECTOR_API_HOST=0.0.0.0
VECTOR_API_PORT=8001
```

### 3. Database Migration

Run Django migrations to create the new models:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Usage

### Automatic Processing

The system automatically processes scraped pages when `ENABLE_AUTO_SUMMARIZATION=True`:

1. **Scraping**: Pages are scraped using existing workflow
2. **Organization**: Content is stored in structured directories
3. **Summarization**: AI generates dense summaries for each page
4. **Embedding**: Summaries are converted to vector embeddings
5. **Storage**: Embeddings are stored in Milvus database

### Manual Processing

Use the Django management command for batch processing:

```bash
# Process all domains
python manage.py process_summaries --all-domains

# Process specific domain
python manage.py process_summaries --domain example.com

# Process specific job
python manage.py process_summaries --job-id <job-uuid>

# Reprocess failed pages
python manage.py process_summaries --reprocess --max-pages 100
```

### Vector Search API

Start the FastAPI search service:

```bash
python start_vector_api.py
```

The API will be available at `http://localhost:8001` with the following endpoints:

#### Search Documents
```bash
POST /search
{
  "query": "artificial intelligence machine learning",
  "limit": 10,
  "domain": "example.com",  # optional
  "threshold": 0.7          # optional
}
```

#### Get Document Details
```bash
GET /document/{summary_id}
```

#### Trigger Reindexing
```bash
POST /reindex
POST /reindex/domain/{domain}
```

#### Get Statistics
```bash
GET /stats
```

## File Structure

The system creates the following directory structure:

```
scraped_data/
├── pages/
│   └── example.com/
│       ├── index.html
│       ├── index.txt
│       ├── index.json
│       └── products/
│           ├── item-1.html
│           ├── item-1.txt
│           └── item-1.json
└── summaries/
    └── example.com/
        ├── index.txt
        └── products/
            └── item-1.txt
```

## Database Schema

### PageSummary Model
- Links to ScrapedPage (one-to-one)
- Stores dense AI-generated summaries
- Tracks processing metadata and quality metrics
- References file storage paths

### DocumentEmbedding Model
- Links to PageSummary (many-to-one)
- Stores embedding metadata and Milvus IDs
- Tracks vector dimensions and processing info

### Milvus Collection Schema
- **id**: Primary key (varchar)
- **embedding**: Vector data (float_vector, 3072 dims)
- **summary_id**: Django model reference
- **url**: Original document URL
- **domain**: Document domain
- **created_at**: Timestamp

## Performance Characteristics

### Throughput Limits
- **Azure OpenAI**: 15M tokens/minute, 100k requests/minute
- **OpenAI Embeddings**: Hundreds of thousands of requests/minute
- **Milvus Lite**: Optimized for local high-performance search

### Processing Times
- **Summarization**: ~2-5 seconds per page (varies with content length)
- **Embedding**: ~0.1-0.5 seconds per summary
- **Search**: <100ms for similarity queries

### Storage Requirements
- **Original Content**: Full HTML + extracted text
- **Summaries**: ~5-15% of original content size
- **Embeddings**: 3072 dimensions × 4 bytes = ~12KB per document

## API Integration

The system integrates seamlessly with existing scraping workflows:

### Scraping Service Integration
```python
# Auto-summarization happens after successful scraping
results = scraping_service.scrape_domain(domain, job)
# results now includes 'summarization_stats' if enabled
```

### Manual Pipeline Trigger
```python
from scraper.summarization_pipeline import SummarizationPipeline

pipeline = SummarizationPipeline()
stats = pipeline.process_scraped_pages(job_id="uuid")
```

### Search Integration
```python
from scraper.milvus_service import get_milvus_service
from scraper.ai_services import AzureOpenAIEmbeddingService

milvus = get_milvus_service()
embedding_service = AzureOpenAIEmbeddingService()

query_embedding = embedding_service.generate_embedding("search query")
results = milvus.search_similar(query_embedding, limit=10)
```

## Monitoring & Maintenance

### Statistics & Monitoring
- Django admin interface shows summaries and embeddings
- Vector API `/stats` endpoint provides system metrics
- File organization service tracks storage statistics

### Error Handling
- Comprehensive logging for all processing steps
- Graceful degradation when AI services are unavailable
- Retry mechanisms for transient failures

### Performance Optimization
- Batch processing for large datasets
- Memory-efficient streaming processing
- Milvus index optimization for fast searches

## Production Deployment

### Scaling Considerations
- Separate vector API service can be horizontally scaled
- Milvus Lite suitable for moderate scales (millions of documents)
- Consider Milvus cluster for larger deployments

### Security
- API key protection for Azure OpenAI and OpenAI
- Rate limiting on vector search endpoints
- Input validation and sanitization

### Backup & Recovery
- Regular backup of Milvus database file
- Summary files provide recovery mechanism
- Django database contains metadata for rebuilding

## Troubleshooting

### Common Issues

1. **Azure OpenAI Rate Limits**: Implement exponential backoff
2. **Milvus Connection Errors**: Check database file permissions
3. **Memory Issues**: Reduce batch sizes for large processing jobs
4. **Slow Searches**: Ensure Milvus collection is loaded and indexed

### Debug Commands

```bash
# Check processing pipeline stats
python manage.py shell -c "
from scraper.summarization_pipeline import SummarizationPipeline
pipeline = SummarizationPipeline()
print(pipeline.get_pipeline_stats())
"

# Test vector search
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "limit": 5}'
```

This integration provides a complete enterprise-grade vector database backend that seamlessly extends the existing web scraping platform with AI-powered semantic search capabilities.
