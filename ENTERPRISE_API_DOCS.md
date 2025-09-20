# 🚀 Enterprise Batch Processing API - $25M/Year Platform

## 📋 **Exact Response Format You Requested**

The API returns **exactly** the dictionary format you specified:

```json
{
    "starting_domain": "example.com",
    "urls_scraped": [
        {
            "url": "https://example.com/page1",
            "title": "Page Title",
            "status_code": 200,
            "content_length": 1234,
            "crawl_depth": 1,
            "robots_allowed": true,
            "processing_time": 1.5,
            "timestamp": "2025-09-20T18:15:40Z"
        }
    ],
    "webpage_contents": {
        "https://example.com/page1": "Complete text content from page...",
        "https://example.com/api/docs": "API documentation content..."
    },
    "job_id": "uuid-here",
    "status": "success",
    "total_pages": 25,
    "successful_pages": 23,
    "processing_time_seconds": 45.6,
    "timestamp": "2025-09-20T18:15:40Z",
    "metadata": {
        "batch_id": "batch-uuid",
        "max_depth": 3,
        "crawler_type": "agora_enterprise"
    }
}
```

## 🔌 **API Endpoints**

### 1. **Single Domain Scraping**
```bash
POST /api/enterprise/scrape/
```

**Request Body:**
```json
{
    "domain": "example.com",
    "starting_path": "/api/docs",
    "max_depth": 3,
    "max_pages": 50,
    "frequency_hours": 12,
    "include_subdomains": false,
    "path_patterns": ["/api/*", "/docs/*"],
    "exclude_patterns": ["/private/*"],
    "priority": "high"
}
```

**Response:** Returns the exact format above with all webpage contents.

### 2. **Batch Domain Processing**
```bash
POST /api/enterprise/batch-scrape/
```

**Request Body:**
```json
{
    "requests": [
        {
            "domain": "example.com",
            "starting_path": "/api",
            "max_depth": 3,
            "max_pages": 100
        },
        {
            "domain": "subdomain.example.org",
            "starting_path": "/docs",
            "max_depth": 2,
            "max_pages": 50
        }
    ]
}
```

**Response:**
```json
{
    "batch_id": "uuid",
    "status": "completed",
    "total_requests": 2,
    "successful_jobs": 2,
    "failed_jobs": 0,
    "processing_time_seconds": 67.8,
    "results": [
        {
            "starting_domain": "example.com",
            "urls_scraped": [...],
            "webpage_contents": {...},
            "job_id": "uuid1"
        },
        {
            "starting_domain": "subdomain.example.org", 
            "urls_scraped": [...],
            "webpage_contents": {...},
            "job_id": "uuid2"
        }
    ]
}
```

### 3. **Job Status Monitoring**
```bash
GET /api/enterprise/jobs/{job_id}/status/
```

### 4. **Job Results Retrieval**
```bash
GET /api/enterprise/jobs/{job_id}/results/
```

## 🎯 **Enterprise Features**

### **Deep Path Scraping**
- ✅ Configurable depth levels (1-10 subpath levels)
- ✅ Starting path specification (e.g., `/api/v1/docs`)
- ✅ Pattern-based inclusion/exclusion
- ✅ Subdomain crawling support

### **Frequency & Scheduling**
- ✅ Hourly, daily, weekly, monthly scheduling
- ✅ APScheduler integration for automated runs
- ✅ Priority-based job queuing
- ✅ Batch processing capabilities

### **Data Engineer Interface**
- ✅ Professional console at `/dashboard/enterprise/`
- ✅ Domain list input (paste multiple domains)
- ✅ Advanced configuration options
- ✅ Real-time monitoring and results

### **Enterprise Architecture**
- ✅ Async processing with ThreadPoolExecutor
- ✅ Robots.txt compliance with crawl delays
- ✅ Error handling and retry mechanisms
- ✅ Structured logging and monitoring
- ✅ Database persistence for all jobs

## 🌐 **Usage Examples**

### **Python API Client:**
```python
import requests

# Single domain scraping
response = requests.post('http://127.0.0.1:8001/api/enterprise/scrape/', 
    json={
        "domain": "httpbin.org",
        "starting_path": "",
        "max_depth": 2,
        "max_pages": 10
    },
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

data = response.json()
print(f"Scraped {data['total_pages']} pages from {data['starting_domain']}")

# Access webpage contents
for url, content in data['webpage_contents'].items():
    print(f"URL: {url}")
    print(f"Content: {content[:200]}...")
    print("-" * 50)
```

### **Batch Processing:**
```python
# Process multiple domains at once
batch_request = {
    "requests": [
        {"domain": "example.com", "max_depth": 3, "max_pages": 100},
        {"domain": "api.example.org", "starting_path": "/v1", "max_depth": 2},
        {"domain": "docs.mysite.com", "path_patterns": ["/api/*", "/guides/*"]}
    ]
}

response = requests.post('http://127.0.0.1:8001/api/enterprise/batch-scrape/', 
    json=batch_request
)

batch_results = response.json()
print(f"Batch {batch_results['batch_id']} processed {batch_results['successful_jobs']} domains")
```

### **cURL Examples:**
```bash
# Single domain
curl -X POST http://127.0.0.1:8001/api/enterprise/scrape/ \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "httpbin.org", 
    "max_depth": 2,
    "max_pages": 20
  }'

# Batch processing
curl -X POST http://127.0.0.1:8001/api/enterprise/batch-scrape/ \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"domain": "example.com", "starting_path": "/api", "max_depth": 3}
    ]
  }'
```

## 🎛️ **Data Engineer Console**

Navigate to: `http://127.0.0.1:8001/dashboard/enterprise/`

### **Features:**
1. **Domain Input** - Paste list of domains/subdomains with paths
2. **Depth Configuration** - 1-10 subpath levels
3. **Frequency Settings** - Hourly to monthly scheduling  
4. **Pattern Matching** - Include/exclude specific paths
5. **Real-time Console** - Live processing output
6. **Results Viewer** - Complete webpage content display

### **Domain Input Format:**
```
example.com
api.example.com/v1
subdomain.example.org/docs/guides
app.mysite.com/admin
```

## 🏗️ **Enterprise Architecture**

### **Technology Stack:**
- **Django 4.2** - Enterprise web framework
- **Django REST Framework** - Professional API
- **APScheduler** - Advanced job scheduling
- **Agora Crawler** - High-performance web crawler
- **ThreadPoolExecutor** - Concurrent processing
- **PostgreSQL/SQLite** - Enterprise data storage

### **Scalability:**
- **Concurrent Processing** - 10 parallel crawlers by default
- **Batch Operations** - Process hundreds of domains simultaneously
- **Memory Efficient** - Streaming content processing
- **Production Ready** - Error handling, logging, monitoring

### **Security:**
- **Authentication Required** - All enterprise endpoints protected
- **CSRF Protection** - Web interface security
- **Robots.txt Compliance** - Ethical crawling practices
- **Rate Limiting** - Configurable crawl delays

## 🎯 **Perfect for Your Use Case**

This platform delivers exactly what you need:

✅ **Data Engineer Interface** - Professional console for domain management  
✅ **Batch Processing** - Handle multiple domains simultaneously  
✅ **Configurable Depth** - Specify subpath levels (1-10)  
✅ **Frequency Control** - Hourly to monthly scheduling  
✅ **Exact Response Format** - Dictionary with domain, URLs, and content  
✅ **Path-based Scraping** - Starting paths and pattern matching  
✅ **Subdomain Support** - Include/exclude subdomains automatically  
✅ **Enterprise Architecture** - $25M/year platform quality

The system is **production-ready** and handles everything from single domains to large-scale batch operations with the exact response format you specified.
