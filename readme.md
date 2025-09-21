# Agora
# Enterprise Scraping Platform - TypeScript Edition

A modern, enterprise-grade web scraping platform built with TypeScript, featuring AI-powered content processing and semantic search capabilities.

## 🚀 Features

### Core Capabilities
- **Modern Web Scraping**: Playwright-based scraping with robots.txt compliance
- **AI Content Processing**: Automatic summarization using OpenAI/Azure OpenAI
- **Vector Search**: Semantic search using Milvus vector database
- **Job Queue System**: BullMQ-powered background processing
- **Real-time Dashboard**: Next.js admin interface with live monitoring
- **Enterprise APIs**: High-performance Fastify REST APIs

### Technical Stack
- **Backend**: Node.js + TypeScript + Fastify
- **Database**: PostgreSQL + Prisma ORM
- **Vector DB**: Milvus for semantic search
- **Queue**: BullMQ + Redis
- **Frontend**: Next.js 14 + React + TypeScript
- **Scraping**: Playwright + Cheerio
- **AI**: OpenAI/Azure OpenAI APIs

## 🏗️ Architecture

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Next.js UI   │  │  Fastify API    │  │ Worker Process  │
│   (Port 3000)  │──│  (Port 3001)    │──│   Background    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │      Redis      │  │     Milvus      │
│   (Primary DB)  │  │   (Job Queue)   │  │  (Vector DB)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 🚦 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Milvus 2.3+ (or use Milvus Lite)

### Installation

1. **Clone and install dependencies**:
```bash
git clone <repository-url>
cd backend_nova
npm install
```

2. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up the database**:
```bash
npm run db:generate
npm run db:push
```

4. **Install Playwright browsers**:
```bash
npx playwright install
```

### Development

Start all services in development mode:
```bash
npm run dev
```

This starts:
- API server on http://localhost:3001
- Next.js dashboard on http://localhost:3000
- Background worker process

### Production

Build and start production services:
```bash
npm run build
npm start            # API server
npm run start:worker # Worker process
```

## 📋 Environment Configuration

### Required Variables
```bash
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/scraping_platform"
REDIS_URL="redis://localhost:6379"

# OpenAI
OPENAI_API_KEY="your-openai-key"

# Milvus
MILVUS_HOST="localhost"
MILVUS_PORT=19530
```

### Optional Variables
```bash
# Azure OpenAI (alternative to OpenAI)
AZURE_OPENAI_API_KEY="your-azure-key"
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"

# Performance tuning
MAX_CONCURRENT_JOBS=5
DEFAULT_CRAWL_DELAY=1000
```

## 🎯 API Endpoints

### Domain Management
- `GET /api/domains` - List all domains
- `POST /api/domains` - Create new domain
- `GET /api/domains/:id` - Get domain details
- `PUT /api/domains/:id` - Update domain
- `DELETE /api/domains/:id` - Delete domain

### Job Management
- `GET /api/jobs` - List scraping jobs
- `POST /api/jobs` - Create new job
- `GET /api/jobs/:id` - Get job details
- `POST /api/jobs/:id/cancel` - Cancel job
- `POST /api/jobs/:id/retry` - Retry failed job

### Semantic Search
- `POST /api/search` - Perform semantic search
- `GET /api/search/document/:id` - Get document details
- `GET /api/search/stats` - Search system statistics

### System Health
- `GET /health` - System health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## 🔍 Usage Examples

### Create a Domain
```bash
curl -X POST http://localhost:3001/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Site",
    "baseUrl": "https://example.com",
    "maxDepth": 3,
    "maxPages": 100
  }'
```

### Start a Scraping Job
```bash
curl -X POST http://localhost:3001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "domainId": "domain-uuid",
    "priority": "HIGH"
  }'
```

### Semantic Search
```bash
curl -X POST http://localhost:3001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning best practices",
    "topK": 5
  }'
```

## 🏢 Enterprise Features

### Scalability
- Horizontal worker scaling
- Database connection pooling  
- Redis-based job distribution
- Vector database optimization

### Security
- Request validation and sanitization
- CORS configuration
- Security headers
- Rate limiting ready

### Monitoring
- Structured logging
- Health check endpoints
- Job queue monitoring
- Performance metrics

### Reliability
- Automatic retries
- Graceful error handling
- Circuit breaker patterns
- Database transaction safety

## 🛠️ Development

### Project Structure
```
src/
├── api/              # Fastify API server
│   ├── routes/       # API route handlers  
│   ├── middleware/   # Custom middleware
│   └── server.ts     # Main server setup
├── lib/              # Core business logic
│   ├── scraping/     # Web scraping engine
│   ├── ai/           # AI services
│   ├── vector/       # Vector database
│   ├── queue/        # Job queue system
│   └── utils/        # Utilities
├── workers/          # Background workers
└── types/            # TypeScript definitions

app/                  # Next.js frontend
├── page.tsx          # Dashboard homepage
└── components/       # React components

prisma/
├── schema.prisma     # Database schema
└── migrations/       # Database migrations
```

### Key Services

**ModernScraper**: Playwright-based scraping with robots.txt compliance
**SummarizationService**: AI-powered content summarization  
**EmbeddingService**: Text-to-vector conversion
**MilvusService**: Vector database operations
**ScrapingJobQueue**: Background job processing

### Adding New Features

1. **New API Endpoint**: Add route in `src/api/routes/`
2. **New Worker Task**: Extend `ScrapingWorker` class
3. **New AI Service**: Implement in `src/lib/ai/`
4. **New Database Model**: Update `prisma/schema.prisma`

## 📊 Performance

### Benchmarks
- **Scraping**: 1-5 pages/second depending on site
- **AI Processing**: 2-10 summaries/second
- **Vector Search**: <100ms for typical queries
- **Job Processing**: 5-50 concurrent jobs

### Optimization Tips
- Increase `MAX_CONCURRENT_JOBS` for faster processing
- Use Redis Cluster for job queue scaling
- Configure Milvus for your hardware
- Tune Playwright browser options

## 🚀 Deployment

### Docker (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Manual Deployment
1. Set up PostgreSQL, Redis, and Milvus
2. Build the application: `npm run build`
3. Run migrations: `npm run db:migrate`
4. Start services: `npm start` & `npm run start:worker`

### Cloud Deployment
- **API**: Deploy to any Node.js hosting (Vercel, Railway, etc.)
- **Database**: Use managed PostgreSQL (AWS RDS, etc.)
- **Redis**: Use managed Redis (AWS ElastiCache, etc.)
- **Milvus**: Use Zilliz Cloud or self-hosted

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🆘 Support

For issues and questions:
- Create a GitHub issue
- Check the documentation
- Review the API examples

---

**Built with ❤️ using modern TypeScript and enterprise-grade architecture**

# 🎓 PennGPT - AI-Powered University Assistant

<div align="center">

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-penngpt.com-blue?style=for-the-badge)](https://penngpt.com)
[![API Status](https://img.shields.io/badge/🔧_API-Online-green?style=for-the-badge)](https://api.penngpt.velroi.com)
[![SSL Security](https://img.shields.io/badge/🔒_SSL-Secured-green?style=for-the-badge)](#security)
[![React](https://img.shields.io/badge/⚛️_React-18.3-blue?style=for-the-badge)](#frontend)
[![Python](https://img.shields.io/badge/🐍_Python-FastAPI-yellow?style=for-the-badge)](#backend)

</div>

## 🚀 Overview

**PennGPT** is an intelligent AI assistant specifically designed for the University of Pennsylvania community. Built with cutting-edge RAG (Retrieval-Augmented Generation) technology, it provides accurate, contextual information about Penn academics, student life, events, clubs, and campus resources.

### ✨ Key Features

- 🎯 **Penn-Specific Knowledge**: Comprehensive information about UPenn academics, clubs, events, and resources
- 💬 **Natural Conversations**: Chat-based interface with contextual understanding
- 🔍 **Smart Search**: Vector-powered semantic search across Penn's knowledge base
- 📱 **Responsive Design**: Modern, mobile-friendly React frontend
- 🔒 **Secure & Fast**: SSL-encrypted with optimized performance
- 📚 **Citations**: Provides sources for all information shared

---

## 🌐 Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| **Main Application** | [https://penngpt.com](https://penngpt.com) | 🟢 Live |
| **Secondary Domain** | [https://penngpt.velroi.com](https://penngpt.velroi.com) | 🟢 Live |
| **API Endpoint** | [https://api.penngpt.velroi.com](https://api.penngpt.velroi.com) | 🟢 Live |
| **Health Check** | [/api/health](https://penngpt.com/api/health) | 🟢 Active |

---

## 🏗️ Architecture

```mermaid
graph TB
    A[👤 User] --> B[🌐 HTTPS Frontend<br/>penngpt.com]
    B --> C[🔄 Nginx Reverse Proxy]
    C --> D[⚛️ React SPA<br/>Vite + TypeScript]
    C --> E[🔌 API Proxy<br/>/api/*]
    E --> F[🐍 FastAPI Backend<br/>Python + Uvicorn]
    F --> G[🧠 Azure OpenAI<br/>GPT-4 + Embeddings]
    F --> H[📊 Milvus Vector DB<br/>Semantic Search]
    F --> I[📚 Knowledge Base<br/>Penn Data + Clubs]
    
    style A fill:#e1f5fe
    style B fill:#e8f5e8
    style G fill:#fff3e0
    style H fill:#f3e5f5
    style I fill:#e0f2f1
```

### 🔧 Technology Stack

**Frontend:**
- ⚛️ **React 18.3** with TypeScript
- ⚡ **Vite** for fast development and building
- 🎨 **Tailwind CSS** for modern styling
- 📱 **Responsive Design** with mobile-first approach
- 🔍 **Zustand** for state management

**Backend:**
- 🐍 **Python FastAPI** for high-performance APIs
- 🧠 **Azure OpenAI** (GPT-4, text-embedding-3-large)
- 📊 **Milvus** vector database for semantic search
- 🔄 **Async/Await** for concurrent processing
- 📚 **RAG Pipeline** for contextual responses

**Infrastructure:**
- 🔒 **Nginx** with SSL termination
- 📜 **Let's Encrypt** SSL certificates
- ☁️ **AWS EC2** hosting
- 🌐 **DNS** with multiple domain support
- 🔄 **Auto-renewal** for certificates

---

## 📖 Usage

### 💬 Chat Interface

Simply visit [penngpt.com](https://penngpt.com) and start chatting! Ask about:

- 📚 **Academics**: Course information, requirements, schedules
- 🎭 **Student Life**: Clubs, organizations, events
- 🏛️ **Campus Resources**: Libraries, dining, facilities
- 📅 **Events**: Upcoming activities and deadlines
- ℹ️ **General Info**: Penn policies, contacts, directions

### 🔧 API Usage

**Base URL:** `https://penngpt.com/api/` or `https://api.penngpt.velroi.com/`

#### Chat Endpoint
```bash
curl -X POST https://penngpt.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Tell me about Penn clubs"}
    ],
    "top_k": 5
  }'
```

#### Health Check
```bash
curl https://penngpt.com/api/health
```

**Response Format:**
```json
{
  "answer": "Detailed response with Penn-specific information...",
  "citations": [
    {
      "title": "Source Title",
      "url": "https://example.com",
      "excerpt": "Relevant excerpt..."
    }
  ],
  "session_id": "unique-session-identifier"
}
```

---

## 🚀 Development

### Frontend Setup

```bash
cd frontend/frontend/client
npm install
npm run dev  # Development server on :5173
npm run build  # Production build
```

### Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Configure Azure OpenAI credentials

# Run development server
python -m uvicorn chat_assistant_api:app --reload --host 127.0.0.1 --port 8010
```

### Environment Variables

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Vector Database
MILVUS_DB_PATH=./milvus_lite.db
COLLECTION_NAME=web_documents
```

---

## 🔒 Security

- 🛡️ **SSL/TLS Encryption**: All communications encrypted with Let's Encrypt certificates
- 🔐 **Security Headers**: HSTS, CSP, XSS protection, and more
- 🚫 **CORS Protection**: Properly configured cross-origin policies  
- 🔄 **Auto-Renewal**: Certificates automatically renewed
- 📊 **Rate Limiting**: API endpoint protection
- 🔍 **Input Validation**: Secure request processing

---

## 📊 Features

### 🎯 Core Capabilities

- **🧠 Intelligent Responses**: Context-aware answers using RAG architecture
- **📚 Comprehensive Knowledge**: 1,399+ Penn clubs and extensive university data
- **🔍 Semantic Search**: Vector-based similarity matching for relevant information
- **💬 Conversational Memory**: Maintains context throughout chat sessions
- **📱 Mobile Optimized**: Responsive design works on all devices
- **⚡ Fast Performance**: Optimized for quick response times

### 🔧 Technical Features

- **🔄 Real-time Processing**: Async backend for concurrent request handling
- **📈 Scalable Architecture**: Designed to handle multiple users
- **🎨 Modern UI/UX**: Clean, intuitive chat interface
- **🔗 Citation System**: Provides sources for all information
- **📊 Vector Indexing**: Efficient similarity search across knowledge base
- **🛠️ API-First Design**: RESTful API for integration possibilities

---

## 📈 Project Stats

| Metric | Value |
|--------|-------|
| **Penn Clubs Indexed** | 1,399+ |
| **Knowledge Base Entries** | 10,000+ |
| **Response Time** | < 2 seconds |
| **SSL Certificate Grade** | A+ |
| **Uptime** | 99.9% |
| **Supported Domains** | 3 |

---

## 🤝 Contributing

We welcome contributions to make PennGPT even better!

1. **🍴 Fork** the repository
2. **🌿 Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **💾 Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **📤 Push** to the branch (`git push origin feature/amazing-feature`)
5. **🔄 Open** a Pull Request

---

## 📋 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Main chat interface |
| `GET` | `/health` | Service health check |
| `GET` | `/docs` | Interactive API documentation |

### Request Parameters

**Chat Endpoint:**
- `messages`: Array of conversation messages
- `top_k`: Number of knowledge base results to retrieve (default: 5)
- `session_id`: Optional session identifier for conversation tracking

---

## 📞 Support & Contact

- 🌐 **Website**: [penngpt.com](https://penngpt.com)
- 🔧 **API**: [api.penngpt.velroi.com](https://api.penngpt.velroi.com)
- 📧 **Contact**: [admin@velroi.com](mailto:admin@velroi.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/agora/issues)

---


<div align="center">

**🎓 Built with ❤️ for the University of Pennsylvania community**

[![UPenn](https://img.shields.io/badge/🏛️_University_of-Pennsylvania-red?style=for-the-badge)](https://upenn.edu)

*Empowering Penn students, faculty, and staff with AI-powered assistance*

</div>
