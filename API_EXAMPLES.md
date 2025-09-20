# API Usage Examples

This document provides comprehensive examples of how to use the Scraping Platform API for external integrations.

## Authentication

All API requests require authentication. Use Django session authentication or add API token authentication as needed.

## Base URL

```
http://localhost:8000/api/
```

## Domain Management

### Create a New Domain

```bash
curl -X POST http://localhost:8000/api/domains/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "name": "Tech Blog Scraping",
    "base_url": "https://techcrunch.com/",
    "max_depth": 3,
    "max_pages": 200,
    "scrape_frequency_hours": 12,
    "status": "active",
    "advanced_config": {
      "user_agent": "TechScraper/1.0",
      "delay": 2,
      "respect_robots_txt": true
    }
  }'
```

### Get All Domains

```bash
curl -X GET "http://localhost:8000/api/domains/" \
  -H "Accept: application/json"
```

### Get Domain Details

```bash
curl -X GET "http://localhost:8000/api/domains/{domain_id}/" \
  -H "Accept: application/json"
```

### Trigger Immediate Scraping

```bash
curl -X POST "http://localhost:8000/api/domains/{domain_id}/scrape_now/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token"
```

### Update Domain Configuration

```bash
curl -X PATCH "http://localhost:8000/api/domains/{domain_id}/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "max_pages": 500,
    "scrape_frequency_hours": 6
  }'
```

### Activate/Pause Domain

```bash
# Activate
curl -X POST "http://localhost:8000/api/domains/{domain_id}/activate/" \
  -H "X-CSRFToken: your-csrf-token"

# Pause
curl -X POST "http://localhost:8000/api/domains/{domain_id}/pause/" \
  -H "X-CSRFToken: your-csrf-token"
```

## Bulk Operations

### Bulk Domain Creation

```bash
curl -X POST http://localhost:8000/api/domains/bulk_create/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "urls": [
      "https://example1.com/blog/",
      "https://example2.com/news/",
      "https://example3.com/docs/"
    ],
    "max_depth": 3,
    "max_pages": 100,
    "priority": "medium",
    "advanced_config": {
      "delay": 1,
      "timeout": 30
    }
  }'
```

### Bulk Scraping Request

```bash
curl -X POST http://localhost:8000/api/bulk-scrape/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "urls": [
      "https://news.ycombinator.com/",
      "https://reddit.com/r/programming/",
      "https://dev.to/latest"
    ],
    "priority": "high",
    "max_depth": 2,
    "max_pages": 50
  }'
```

## Job Monitoring

### Get All Jobs

```bash
curl -X GET "http://localhost:8000/api/jobs/" \
  -H "Accept: application/json"
```

### Filter Jobs

```bash
# By status
curl -X GET "http://localhost:8000/api/jobs/?status=running" \
  -H "Accept: application/json"

# By domain
curl -X GET "http://localhost:8000/api/jobs/?domain={domain_id}" \
  -H "Accept: application/json"

# By date range
curl -X GET "http://localhost:8000/api/jobs/?created_at__gte=2024-01-01" \
  -H "Accept: application/json"
```

### Get Job Progress

```bash
curl -X GET "http://localhost:8000/api/jobs/{job_id}/progress/" \
  -H "Accept: application/json"
```

### Get Job Results

```bash
curl -X GET "http://localhost:8000/api/jobs/{job_id}/results/" \
  -H "Accept: application/json"
```

### Get Job Pages

```bash
curl -X GET "http://localhost:8000/api/jobs/{job_id}/pages/" \
  -H "Accept: application/json"
```

## Data Retrieval

### Get Scraped Pages

```bash
# All pages
curl -X GET "http://localhost:8000/api/pages/" \
  -H "Accept: application/json"

# Filter by status
curl -X GET "http://localhost:8000/api/pages/?status=success" \
  -H "Accept: application/json"

# Search in content
curl -X GET "http://localhost:8000/api/pages/?search=python" \
  -H "Accept: application/json"
```

### Get Page Content

```bash
curl -X GET "http://localhost:8000/api/pages/{page_id}/content/" \
  -H "Accept: application/json"
```

## System Statistics

### Get Overall System Stats

```bash
curl -X GET "http://localhost:8000/api/stats/" \
  -H "Accept: application/json"
```

Response example:
```json
{
  "domains": {
    "total": 15,
    "active": 12,
    "paused": 2,
    "error": 1
  },
  "jobs": {
    "total": 148,
    "running": 3,
    "completed": 142,
    "failed": 3
  },
  "pages": {
    "total": 2847,
    "successful": 2801,
    "failed": 46
  },
  "activity": {
    "jobs_today": 12,
    "jobs_this_week": 89,
    "pages_today": 456,
    "pages_this_week": 1823
  },
  "performance": {
    "avg_job_duration_seconds": 45.7,
    "avg_pages_per_job": 19.2,
    "success_rate": 98.4
  },
  "scheduler": {
    "running": true,
    "total_jobs": 12
  }
}
```

## Advanced Usage Examples

### Python Integration

```python
import requests
import json

class ScrapingPlatformAPI:
    def __init__(self, base_url, csrf_token=None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if csrf_token:
            self.session.headers.update({'X-CSRFToken': csrf_token})
    
    def create_domain(self, name, base_url, **kwargs):
        """Create a new scraping domain."""
        data = {
            'name': name,
            'base_url': base_url,
            'max_depth': kwargs.get('max_depth', 3),
            'max_pages': kwargs.get('max_pages', 100),
            'scrape_frequency_hours': kwargs.get('frequency', 24),
            'status': kwargs.get('status', 'active')
        }
        
        if 'advanced_config' in kwargs:
            data['advanced_config'] = kwargs['advanced_config']
        
        response = self.session.post(
            f"{self.base_url}/api/domains/",
            json=data
        )
        return response.json()
    
    def get_job_results(self, job_id):
        """Get complete results for a job."""
        response = self.session.get(
            f"{self.base_url}/api/jobs/{job_id}/results/"
        )
        return response.json()
    
    def monitor_job_progress(self, job_id, callback=None):
        """Monitor job progress with callback."""
        import time
        
        while True:
            response = self.session.get(
                f"{self.base_url}/api/jobs/{job_id}/progress/"
            )
            progress = response.json()
            
            if callback:
                callback(progress)
            
            if progress['status'] in ['completed', 'failed']:
                break
                
            time.sleep(5)
        
        return progress

# Usage example
api = ScrapingPlatformAPI('http://localhost:8000')

# Create domain
domain = api.create_domain(
    name="My Blog Scraper",
    base_url="https://myblog.com/",
    max_depth=2,
    max_pages=50,
    advanced_config={
        "delay": 1.5,
        "user_agent": "MyBot/1.0"
    }
)

print(f"Created domain: {domain['id']}")
```

### JavaScript Integration

```javascript
class ScrapingPlatformAPI {
    constructor(baseUrl, csrfToken = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.csrfToken = csrfToken;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}/api${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (this.csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)) {
            headers['X-CSRFToken'] = this.csrfToken;
        }
        
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        return response.json();
    }
    
    async createDomain(data) {
        return this.request('/domains/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async getSystemStats() {
        return this.request('/stats/');
    }
    
    async monitorJobProgress(jobId, onProgress) {
        const poll = async () => {
            try {
                const progress = await this.request(`/jobs/${jobId}/progress/`);
                onProgress(progress);
                
                if (!['completed', 'failed'].includes(progress.status)) {
                    setTimeout(poll, 5000);
                }
            } catch (error) {
                console.error('Error monitoring job:', error);
            }
        };
        
        poll();
    }
}

// Usage example
const api = new ScrapingPlatformAPI('http://localhost:8000', getCsrfToken());

// Create domain and monitor
api.createDomain({
    name: 'News Site',
    base_url: 'https://news.example.com/',
    max_depth: 3,
    max_pages: 200,
    status: 'active'
}).then(domain => {
    console.log('Domain created:', domain.id);
    
    // Monitor for new jobs on this domain
    // (You would implement WebSocket or polling here)
});
```

### Webhook Integration

```bash
# Set up webhook endpoint to receive scraping results
curl -X POST http://localhost:8000/api/webhooks/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{
    "url": "https://your-app.com/webhook/scraping-results",
    "events": ["job.completed", "job.failed"],
    "secret": "your-webhook-secret"
  }'
```

## Response Formats

### Standard API Response

```json
{
  "domain": "example.com",
  "base_url": "https://example.com/blog/",
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "started_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:30Z",
  "status": "success",
  "pages": [
    {
      "url": "https://example.com/blog/post-1/",
      "title": "Blog Post Title",
      "content": "Extracted text content...",
      "status_code": 200,
      "content_length": 5420,
      "extracted_data": {
        "headings": ["H1 Title", "H2 Subtitle"],
        "links": ["https://example.com/related"],
        "images": ["https://example.com/image.jpg"],
        "meta_description": "Post description...",
        "word_count": 450
      }
    }
  ],
  "summary": {
    "total_pages": 25,
    "successful_pages": 23,
    "failed_pages": 2,
    "total_size_bytes": 128540,
    "processing_time_seconds": 45.2
  }
}
```

### Error Response

```json
{
  "error": "Invalid domain configuration",
  "details": {
    "base_url": ["Enter a valid URL"],
    "max_pages": ["Ensure this value is less than or equal to 10000"]
  },
  "code": "validation_error"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Authenticated users**: 1000 requests/hour
- **Domain creation**: 10 domains/hour
- **Bulk operations**: 5 operations/hour

Headers returned:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641024000
```

## Best Practices

1. **Use pagination** for large datasets:
   ```bash
   curl "http://localhost:8000/api/pages/?page=2&page_size=50"
   ```

2. **Filter results** to reduce response size:
   ```bash
   curl "http://localhost:8000/api/jobs/?status=completed&limit=10"
   ```

3. **Monitor job progress** instead of polling results:
   ```bash
   curl "http://localhost:8000/api/jobs/{job_id}/progress/"
   ```

4. **Use bulk operations** for efficiency:
   ```bash
   curl -X POST "http://localhost:8000/api/bulk-scrape/"
   ```

5. **Handle errors gracefully** and implement retry logic

6. **Cache responses** when appropriate to reduce API calls

## Error Handling

Common HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

Always check the response status and handle errors appropriately in your integration code.
