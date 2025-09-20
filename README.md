# Enterprise Scraping Platform

A professional-grade web scraping platform built with Django, featuring automated scheduling, real-time monitoring, and comprehensive data management capabilities.

## 🚀 Features

### Core Functionality
- **Domain Management**: Configure domains with custom scraping parameters
- **Automated Scheduling**: APScheduler-based job management with configurable intervals
- **Real-time Monitoring**: Live dashboard with job progress tracking
- **Data Storage**: Comprehensive data models with full audit trails
- **API Integration**: RESTful API for external system integration

### Professional Features
- **Enterprise Dashboard**: Modern, responsive UI with real-time updates
- **Batch Operations**: Bulk domain creation and management
- **Advanced Configuration**: JSON-based configuration for complex scenarios
- **Performance Analytics**: Detailed statistics and performance metrics
- **Template System**: Reusable scraping configurations
- **Error Handling**: Comprehensive error tracking and retry mechanisms

### Technical Excellence
- **Production-Ready**: Proper logging, caching, and database optimization
- **Scalable Architecture**: Designed for high-volume operations
- **Security**: CSRF protection, authentication, and input validation
- **Extensible**: Clean architecture for easy feature additions
- **API-First**: Complete REST API with documentation

## 📋 Requirements

- Python 3.8+
- Django 4.2+
- SQLite/PostgreSQL/MySQL
- Redis (optional, for caching)

## ⚡ Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd backend_nova

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env file with your settings
nano .env
```

### 3. Database Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata fixtures/initial_data.json
```

### 4. Start Services

```bash
# Start Django development server
python manage.py runserver

# In another terminal, start the scheduler
python manage.py start_scheduler
```

### 5. Access the Platform

- **Dashboard**: http://localhost:8000/dashboard/
- **Admin Interface**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **API Root**: http://localhost:8000/api/

## 🔧 Configuration Guide

### Environment Variables

Key configuration options in `.env`:

```env
# Basic Django settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Scheduler settings
SCHEDULER_MAX_WORKERS=10
SCHEDULER_DATABASE_URL=sqlite:///scheduler_jobs.sqlite

# Scraping configuration
SCRAPING_DEFAULT_TIMEOUT=30
SCRAPING_MAX_RETRIES=3
```

### Advanced Configuration

For production deployment, consider:

1. **Database**: Switch to PostgreSQL or MySQL
2. **Caching**: Configure Redis for better performance
3. **Security**: Enable HTTPS and security headers
4. **Monitoring**: Set up proper logging and monitoring
5. **Scaling**: Configure multiple workers and load balancing

## 📖 Usage Guide

### Adding Domains

1. **Via Dashboard**:
   - Navigate to Dashboard → Domains → Add Domain
   - Fill in the form with domain details
   - Configure scraping parameters
   - Save and activate

2. **Via API**:
   ```bash
   curl -X POST http://localhost:8000/api/domains/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Example Blog",
       "base_url": "https://example.com/blog/",
       "max_depth": 3,
       "max_pages": 100,
       "scrape_frequency_hours": 24,
       "status": "active"
     }'
   ```

3. **Bulk Creation**:
   ```bash
   curl -X POST http://localhost:8000/api/bulk-scrape/ \
     -H "Content-Type: application/json" \
     -d '{
       "urls": [
         "https://example1.com/blog/",
         "https://example2.com/docs/"
       ],
       "max_depth": 3,
       "max_pages": 50
     }'
   ```

### Monitoring Jobs

- **Dashboard**: Real-time job monitoring with progress bars
- **Job Details**: Click on any job to see detailed information
- **API Monitoring**: Use `/api/jobs/{id}/progress/` for real-time updates

### Retrieving Data

1. **Via Dashboard**: Browse scraped pages and export data
2. **Via API**: Access structured data through REST endpoints
3. **Database**: Direct database access for advanced queries

## 🔌 API Reference

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/domains/` | GET, POST | List/create domains |
| `/api/domains/{id}/` | GET, PUT, DELETE | Domain details |
| `/api/domains/{id}/scrape_now/` | POST | Trigger immediate scraping |
| `/api/jobs/` | GET | List scraping jobs |
| `/api/jobs/{id}/progress/` | GET | Real-time job progress |
| `/api/jobs/{id}/results/` | GET | Complete job results |
| `/api/pages/` | GET | List scraped pages |
| `/api/stats/` | GET | System statistics |

### Response Format

All API responses follow this structure:

```json
{
  "domain": "example.com",
  "base_url": "https://example.com/blog/",
  "job_id": "uuid-here",
  "started_at": "2024-01-01T12:00:00Z",
  "pages": [
    {
      "url": "https://example.com/blog/post-1/",
      "title": "Blog Post Title",
      "content": "Extracted text content...",
      "status_code": 200,
      "extracted_data": {
        "headings": ["H1", "H2"],
        "links": ["url1", "url2"],
        "images": ["img1.jpg"]
      }
    }
  ],
  "summary": {
    "total_pages": 25,
    "successful_pages": 23,
    "failed_pages": 2,
    "processing_time_seconds": 45.2
  }
}
```

## 🛠 Management Commands

The platform includes several Django management commands:

```bash
# Start the scheduler
python manage.py start_scheduler

# Stop the scheduler
python manage.py stop_scheduler

# Sync domain schedules
python manage.py sync_schedules

# Clean old data
python manage.py cleanup_old_data --days 30

# Export domain data
python manage.py export_domains --format json

# Import domains from CSV
python manage.py import_domains domains.csv
```

## 🏗 Architecture

### Components

1. **Django Apps**:
   - `scraper`: Core scraping models and services
   - `scheduler`: APScheduler integration
   - `dashboard`: Web interface

2. **Services**:
   - `ScrapingService`: Handles actual scraping operations
   - `ScrapingScheduler`: Manages job scheduling
   - `ApiIntegrationService`: External API integration

3. **Models**:
   - `Domain`: Scraping configuration
   - `ScrapingJob`: Job execution records
   - `ScrapedPage`: Individual page data
   - `ScrapingTemplate`: Reusable configurations

### Data Flow

1. User configures domain via dashboard or API
2. Scheduler creates periodic jobs
3. ScrapingService executes scraping
4. Results stored in database
5. Data accessible via dashboard/API

## 🔒 Security

### Features

- **Authentication**: Required for all operations
- **CSRF Protection**: Enabled for all forms
- **Input Validation**: Comprehensive data validation
- **Rate Limiting**: Configurable request throttling
- **Secure Headers**: Production security headers

### Best Practices

1. **Environment Variables**: Never commit secrets
2. **Database Security**: Use strong credentials
3. **HTTPS**: Always use HTTPS in production
4. **Regular Updates**: Keep dependencies updated
5. **Monitoring**: Monitor for suspicious activity

## 📊 Monitoring & Debugging

### Logging

Logs are configured at multiple levels:

- **Application Logs**: `logs/django.log`
- **Scheduler Logs**: `logs/scheduler.log`
- **Error Logs**: Separate error logging

### Metrics

System metrics are automatically collected:

- Job execution times
- Success rates
- System resource usage
- API response times

### Health Checks

Built-in health check endpoints:

- `/api/stats/`: System statistics
- `/scheduler/api/status/`: Scheduler status
- `/admin/`: Admin interface health

## 🚀 Deployment

### Production Checklist

1. **Environment Configuration**:
   ```env
   DEBUG=False
   SECRET_KEY=secure-production-key
   ALLOWED_HOSTS=your-domain.com
   ```

2. **Database**: Use PostgreSQL or MySQL
3. **Static Files**: Configure WhiteNoise or CDN
4. **Process Management**: Use Gunicorn + Nginx
5. **Monitoring**: Set up logging and monitoring
6. **Backups**: Regular database backups

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["gunicorn", "scraping_platform.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. **Documentation**: Check this README and code comments
2. **Issues**: Open GitHub issues for bugs
3. **API Docs**: Visit `/api/docs/` for API documentation
4. **Admin Interface**: Use `/admin/` for direct data management

## 🔄 Changelog

### Version 1.0.0 (2024-01-01)
- Initial release
- Core scraping functionality
- Dashboard interface
- REST API
- Automated scheduling
- Comprehensive documentation

---

**Built with ❤️ for enterprise-grade web scraping operations**
