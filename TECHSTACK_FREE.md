# Free & Open Source Technology Stack

## Complete Free Technology Stack for Vendor Risk Control Tower

This document outlines a 100% free and open-source technology stack for building the multi-agent vendor risk assessment system. All components are either free to use, open-source, or have generous free tiers.

---

## Core Backend Stack

### Application Framework
**FastAPI** (Free, MIT License)
- Modern Python web framework
- Async support
- Automatic API documentation
- High performance
- Easy to learn and use

**Alternative:** Flask (Free, BSD License)

### Programming Language
**Python 3.11+** (Free, PSF License)
- Excellent AI/ML ecosystem
- LangChain/LangGraph support
- Rich library ecosystem
- Easy to maintain

---

## LLM & AI Stack

### LLM Provider Options

**Option 1: Ollama (100% Free, Self-Hosted)**
- Run LLMs locally
- No API costs
- Privacy-first
- Models: Llama 3, Mistral, Mixtral, CodeLlama
- Installation: Simple, works on CPU/GPU
- **Recommended for development and small-scale production**

**Option 2: OpenAI Free Tier**
- $5 free credits for new accounts
- Pay-as-you-go after that
- GPT-3.5-turbo: Very affordable
- GPT-4: More expensive but better reasoning

**Option 3: Anthropic Claude (Free Trial)**
- Free trial credits
- Claude Sonnet: Good balance of cost/performance
- Pay-as-you-go after trial

**Option 4: Groq (Free Tier)**
- Fast inference
- Free tier available
- Llama 3, Mixtral models
- Good for production

**Recommended:** Start with Ollama for development, move to Groq free tier for production

### Agent Framework
**LangChain** (Free, MIT License)
- Tool integration
- Agent creation
- Prompt management
- Memory management

**LangGraph** (Free, MIT License)
- Multi-agent orchestration
- State machine management
- Parallel execution
- Built on LangChain

### Embeddings

**Option 1: Sentence Transformers (100% Free, Self-Hosted)**
- all-MiniLM-L6-v2 (384 dimensions)
- all-mpnet-base-v2 (768 dimensions)
- Run locally, no API costs
- Good quality embeddings
- **Recommended**

**Option 2: OpenAI Embeddings**
- text-embedding-3-small: Very affordable
- text-embedding-3-large: Better quality
- Pay-as-you-go

**Recommended:** Sentence Transformers for free operation

---

## Database Stack

### Primary Database
**PostgreSQL 15+** (Free, PostgreSQL License)
- Robust and reliable
- JSONB support for flexible schemas
- Full-text search
- Excellent performance
- Wide ecosystem

**Hosting Options:**
- Self-hosted (Docker/VM)
- Supabase (Free tier: 500MB database, 2GB bandwidth)
- ElephantSQL (Free tier: 20MB)
- Neon (Free tier: 3GB storage)

**Recommended:** Self-hosted PostgreSQL in Docker or Supabase free tier

### Caching & State Management
**Redis** (Free, BSD License)
- In-memory data store
- Fast caching
- Pub/sub for real-time updates
- Session management

**Hosting Options:**
- Self-hosted (Docker/VM)
- Redis Cloud (Free tier: 30MB)
- Upstash (Free tier: 10,000 commands/day)

**Recommended:** Self-hosted Redis in Docker

---

## Vector Database

### Vector Store Options

**Option 1: Qdrant (100% Free, Self-Hosted, Apache 2.0)**
- Open-source vector database
- Docker deployment
- Excellent performance
- REST API
- Web UI included
- **Recommended for full control**

**Option 2: Chroma (100% Free, Self-Hosted, Apache 2.0)**
- Lightweight vector database
- Easy to set up
- Python-native
- Good for development

**Option 3: Weaviate (Free, Self-Hosted, BSD License)**
- Open-source vector database
- GraphQL API
- Good scalability

**Option 4: Pinecone (Free Tier)**
- Managed service
- Free tier: 1 index, 100K vectors
- Easy to use
- Limited free tier

**Recommended:** Qdrant self-hosted for production, Chroma for development

---

## Document Processing

### PDF Processing
**PyPDF2** (Free, BSD License)
- Basic PDF text extraction
- Metadata extraction
- Free and simple

**pdfplumber** (Free, MIT License)
- Better text extraction
- Table extraction
- Layout analysis

**Recommended:** pdfplumber for better quality

### Word Documents
**python-docx** (Free, MIT License)
- Read/write DOCX files
- Extract text and formatting
- Table extraction

### Excel Files
**openpyxl** (Free, MIT License)
- Read/write XLSX files
- Formula support
- Data extraction

**pandas** (Free, BSD License)
- Data manipulation
- Excel reading
- CSV support

### OCR (Optical Character Recognition)
**Tesseract OCR** (Free, Apache 2.0)
- Open-source OCR engine
- Multi-language support
- Good accuracy
- Python wrapper: pytesseract

**EasyOCR** (Free, Apache 2.0)
- Deep learning-based OCR
- Better accuracy than Tesseract
- Multi-language support

**Recommended:** EasyOCR for better accuracy

### Document Parsing Framework
**Unstructured.io** (Free, Apache 2.0)
- Unified document parsing
- Supports PDF, DOCX, HTML, etc.
- Layout detection
- Table extraction

---

## Email Service

### Email Sending Options

**Option 1: SMTP (100% Free)**
- Use Gmail SMTP (free for low volume)
- Use your own mail server
- Python: smtplib (built-in)
- **Recommended for development**

**Option 2: Mailgun (Free Tier)**
- 5,000 emails/month free
- Good deliverability
- Email tracking
- API-based

**Option 3: SendGrid (Free Tier)**
- 100 emails/day free
- Email templates
- Analytics
- API-based

**Option 4: Brevo (formerly Sendinblue) (Free Tier)**
- 300 emails/day free
- Email templates
- SMTP and API

**Option 5: Resend (Free Tier)**
- 100 emails/day free
- Modern API
- Good documentation

**Recommended:** Mailgun or Brevo free tier for production, Gmail SMTP for development

---

## External APIs (Free Tiers)

### Credit Rating Alternative
**Option 1: Mock Service (100% Free)**
- Create mock credit rating service
- Use for development and demo
- Implement real integration later

**Option 2: OpenCorporates API (Free)**
- Company information
- Basic company data
- Free tier available

**Option 3: Companies House API (Free, UK)**
- UK company information
- Financial filings
- Free to use

**Recommended:** Mock service for development, OpenCorporates for basic company info

### Breach Data
**HaveIBeenPwned API (Free)**
- Breach lookup
- Free for non-commercial use
- Rate limited
- Good coverage

**Alternative:** Build internal breach database from public sources

### Security Scanning
**Option 1: SSL Labs API (Free)**
- SSL/TLS testing
- Free to use
- Rate limited

**Option 2: SecurityHeaders.com (Free)**
- Security header checking
- Free API

**Option 3: Mozilla Observatory (Free)**
- Website security scanning
- Free API

**Recommended:** Combination of SSL Labs + SecurityHeaders.com

---

## Frontend Stack

### Framework
**React 18** (Free, MIT License)
- Modern UI library
- Large ecosystem
- Excellent documentation

**Vite** (Free, MIT License)
- Fast build tool
- Hot module replacement
- Better than Create React App

### Language
**TypeScript** (Free, Apache 2.0)
- Type safety
- Better IDE support
- Fewer runtime errors

### Styling
**TailwindCSS** (Free, MIT License)
- Utility-first CSS
- Fast development
- Responsive design
- Small bundle size

### UI Components
**shadcn/ui** (Free, MIT License)
- Beautiful components
- Built on Radix UI
- Customizable
- Copy-paste components

**Alternative:** Headless UI (Free, MIT License)

### State Management
**Zustand** (Free, MIT License)
- Simple state management
- Lightweight
- Easy to learn

**Alternative:** React Query for server state

### Data Fetching
**React Query (TanStack Query)** (Free, MIT License)
- Server state management
- Caching
- Automatic refetching
- Excellent DX

### Charts & Visualization
**Recharts** (Free, MIT License)
- React chart library
- Responsive
- Customizable

**Alternative:** Chart.js (Free, MIT License)

### Icons
**Lucide React** (Free, ISC License)
- Beautiful icons
- Tree-shakeable
- Consistent design

**Alternative:** Heroicons (Free, MIT License)

---

## Real-Time Communication

### WebSocket
**Socket.IO** (Free, MIT License)
- Real-time bidirectional communication
- Fallback support
- Room support
- Easy to use

**Alternative:** Native WebSocket API (built-in)

---

## Testing Stack

### Backend Testing
**pytest** (Free, MIT License)
- Python testing framework
- Fixtures
- Parametrization
- Excellent plugins

**pytest-asyncio** (Free, Apache 2.0)
- Async test support

**pytest-cov** (Free, MIT License)
- Code coverage

**httpx** (Free, BSD License)
- HTTP client for testing
- Async support

### Frontend Testing
**Vitest** (Free, MIT License)
- Fast unit testing
- Vite-native
- Jest-compatible API

**React Testing Library** (Free, MIT License)
- Component testing
- User-centric testing

**Playwright** (Free, Apache 2.0)
- E2E testing
- Cross-browser
- Auto-wait
- Better than Selenium

**Alternative:** Cypress (Free, MIT License)

### Load Testing
**Locust** (Free, MIT License)
- Python-based load testing
- Distributed testing
- Web UI

**Alternative:** k6 (Free, AGPL)

---

## Monitoring & Observability

### Metrics
**Prometheus** (Free, Apache 2.0)
- Time-series database
- Metrics collection
- Alerting
- Industry standard

### Dashboards
**Grafana** (Free, AGPL)
- Beautiful dashboards
- Multiple data sources
- Alerting
- Community dashboards

### Logging
**Option 1: Loki + Promtail (Free, AGPL)**
- Log aggregation
- Integrates with Grafana
- Lightweight
- **Recommended**

**Option 2: ELK Stack (Free, Elastic License)**
- Elasticsearch
- Logstash
- Kibana
- More resource-intensive

**Recommended:** Loki for simplicity

### Tracing
**Jaeger** (Free, Apache 2.0)
- Distributed tracing
- OpenTelemetry compatible
- Web UI

**Alternative:** Zipkin (Free, Apache 2.0)

### Application Monitoring
**OpenTelemetry** (Free, Apache 2.0)
- Unified observability
- Metrics, logs, traces
- Vendor-neutral

### Error Tracking
**Sentry (Free Tier)**
- 5,000 events/month free
- Error tracking
- Performance monitoring
- Release tracking

**Alternative:** Self-hosted Sentry (Free, BSL)

---

## Deployment & Infrastructure

### Containerization
**Docker** (Free, Apache 2.0)
- Container runtime
- Image building
- Docker Compose for local dev

**Docker Compose** (Free, Apache 2.0)
- Multi-container orchestration
- Perfect for development

### Container Orchestration
**Kubernetes (K8s)** (Free, Apache 2.0)
- Container orchestration
- Auto-scaling
- Self-healing
- Industry standard

**K3s** (Free, Apache 2.0)
- Lightweight Kubernetes
- Perfect for small deployments
- Less resource-intensive

**MicroK8s** (Free, Apache 2.0)
- Lightweight Kubernetes
- Easy to install
- Good for development

**Recommended:** K3s for production, Docker Compose for development

### Kubernetes Management
**k9s** (Free, Apache 2.0)
- Terminal UI for Kubernetes
- Easy cluster management

**Lens** (Free, MIT License)
- Kubernetes IDE
- Visual cluster management

### CI/CD
**GitHub Actions** (Free for public repos, 2,000 minutes/month for private)
- Integrated with GitHub
- Easy to configure
- Good ecosystem

**GitLab CI** (Free tier available)
- Integrated with GitLab
- Powerful pipelines

**Jenkins** (Free, MIT License)
- Self-hosted
- Highly customizable
- Large plugin ecosystem

**Recommended:** GitHub Actions for simplicity

### Infrastructure as Code
**Terraform** (Free, MPL 2.0)
- Infrastructure provisioning
- Multi-cloud support
- State management

**Ansible** (Free, GPL)
- Configuration management
- Agentless
- YAML-based

### Reverse Proxy / Load Balancer
**Nginx** (Free, BSD License)
- High-performance web server
- Reverse proxy
- Load balancing

**Traefik** (Free, MIT License)
- Modern reverse proxy
- Automatic HTTPS
- Kubernetes-native

**Caddy** (Free, Apache 2.0)
- Automatic HTTPS
- Simple configuration
- Modern

**Recommended:** Traefik for Kubernetes, Nginx for traditional deployments

---

## Cloud Hosting (Free Tiers)

### Application Hosting

**Option 1: Self-Hosted (100% Free)**
- Your own server/VPS
- Full control
- No vendor lock-in

**Option 2: Fly.io (Free Tier)**
- 3 shared-cpu VMs
- 3GB persistent storage
- Good for small apps

**Option 3: Railway (Free Tier)**
- $5 free credits/month
- Easy deployment
- Good DX

**Option 4: Render (Free Tier)**
- Free web services
- 750 hours/month
- Auto-deploy from Git

**Option 5: Heroku (Free Tier Discontinued)**
- No longer free
- Not recommended

**Recommended:** Fly.io or Railway for small deployments, self-hosted for production

### Database Hosting

**Supabase (Free Tier)**
- 500MB PostgreSQL database
- 2GB bandwidth
- Realtime subscriptions
- Auth included

**Neon (Free Tier)**
- 3GB PostgreSQL storage
- Serverless Postgres
- Branching

**ElephantSQL (Free Tier)**
- 20MB PostgreSQL
- Good for development

**PlanetScale (Free Tier)**
- 5GB MySQL storage
- 1 billion row reads/month
- Branching

**Recommended:** Supabase or Neon for PostgreSQL

### Object Storage

**Cloudflare R2 (Free Tier)**
- 10GB storage
- No egress fees
- S3-compatible

**Backblaze B2 (Free Tier)**
- 10GB storage
- 1GB daily download
- S3-compatible

**MinIO (Self-Hosted, Free, AGPL)**
- S3-compatible object storage
- Self-hosted
- High performance

**Recommended:** MinIO self-hosted or Cloudflare R2

### CDN

**Cloudflare (Free Tier)**
- Unlimited bandwidth
- DDoS protection
- SSL certificates
- DNS

**jsDelivr (Free)**
- Free CDN for open source
- NPM, GitHub integration

**Recommended:** Cloudflare for everything

---

## Development Tools

### Code Editor
**VS Code** (Free, MIT License)
- Excellent Python/TypeScript support
- Extensions ecosystem
- Integrated terminal
- Git integration

### API Testing
**Postman (Free Tier)**
- API testing
- Collections
- Environments

**Insomnia** (Free, MIT License)
- API testing
- GraphQL support
- Open source

**HTTPie** (Free, BSD License)
- Command-line HTTP client
- User-friendly

### Database Management
**DBeaver** (Free, Apache 2.0)
- Universal database tool
- PostgreSQL support
- SQL editor

**pgAdmin** (Free, PostgreSQL License)
- PostgreSQL administration
- Web-based

### Version Control
**Git** (Free, GPL)
- Version control
- Industry standard

**GitHub** (Free for public repos)
- Code hosting
- CI/CD
- Issue tracking

**GitLab** (Free tier available)
- Code hosting
- CI/CD
- Issue tracking

---

## Security Tools

### Secrets Management
**Option 1: Environment Variables (Free)**
- Simple and effective
- Use .env files
- Never commit secrets

**Option 2: HashiCorp Vault (Free, MPL 2.0)**
- Secrets management
- Encryption as a service
- Self-hosted

**Option 3: Doppler (Free Tier)**
- Secrets management
- Team collaboration
- Free for small teams

**Recommended:** Environment variables for development, Vault for production

### Vulnerability Scanning
**Trivy** (Free, Apache 2.0)
- Container image scanning
- Dependency scanning
- Fast and accurate

**Snyk (Free Tier)**
- Dependency scanning
- Container scanning
- Free for open source

**OWASP Dependency-Check** (Free, Apache 2.0)
- Dependency vulnerability scanning
- Multiple language support

### SSL Certificates
**Let's Encrypt** (Free)
- Free SSL certificates
- Automated renewal
- Trusted by browsers

**Certbot** (Free, Apache 2.0)
- Let's Encrypt client
- Automatic renewal

---

## Complete Free Stack Summary

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Database:** PostgreSQL (self-hosted or Supabase)
- **Cache:** Redis (self-hosted)
- **Vector DB:** Qdrant (self-hosted)

### AI/ML
- **LLM:** Ollama (self-hosted) or Groq (free tier)
- **Agent Framework:** LangChain + LangGraph
- **Embeddings:** Sentence Transformers (self-hosted)

### Frontend
- **Framework:** React 18 + Vite
- **Language:** TypeScript
- **Styling:** TailwindCSS
- **Components:** shadcn/ui
- **State:** Zustand + React Query
- **Charts:** Recharts

### Infrastructure
- **Containers:** Docker + Docker Compose
- **Orchestration:** K3s (for production)
- **Reverse Proxy:** Traefik or Nginx
- **CI/CD:** GitHub Actions
- **Hosting:** Fly.io (free tier) or self-hosted

### Monitoring
- **Metrics:** Prometheus
- **Dashboards:** Grafana
- **Logging:** Loki + Promtail
- **Tracing:** Jaeger
- **Errors:** Sentry (free tier)

### External Services
- **Email:** Mailgun (free tier) or Gmail SMTP
- **Breach Data:** HaveIBeenPwned (free)
- **Security Scan:** SSL Labs + SecurityHeaders.com (free)
- **CDN:** Cloudflare (free)

### Development
- **Editor:** VS Code
- **API Testing:** Insomnia
- **DB Tool:** DBeaver
- **Version Control:** Git + GitHub

---

## Cost Breakdown

### 100% Free Option (Self-Hosted)
- **LLM:** Ollama (self-hosted) - $0
- **Database:** PostgreSQL (Docker) - $0
- **Cache:** Redis (Docker) - $0
- **Vector DB:** Qdrant (Docker) - $0
- **Email:** Gmail SMTP - $0
- **Hosting:** Your own server - $0 (if you have one)
- **Total:** $0/month

### Minimal Cost Option (Free Tiers)
- **LLM:** Groq free tier - $0
- **Database:** Supabase free tier - $0
- **Cache:** Upstash free tier - $0
- **Vector DB:** Qdrant (Docker) - $0
- **Email:** Mailgun free tier - $0
- **Hosting:** Fly.io free tier - $0
- **Monitoring:** Grafana Cloud free tier - $0
- **Total:** $0/month (within free tier limits)

### Small Production Option
- **LLM:** Groq or OpenAI (pay-as-you-go) - ~$20-50/month
- **Database:** Supabase Pro - $25/month
- **Hosting:** Fly.io or Railway - $10-20/month
- **Email:** Mailgun - $0 (within free tier)
- **Monitoring:** Grafana Cloud - $0 (within free tier)
- **Total:** ~$55-95/month

---

## Recommended Setup by Stage

### Development Stage
- Ollama for LLM (local)
- PostgreSQL (Docker)
- Redis (Docker)
- Qdrant (Docker)
- Gmail SMTP for email
- Docker Compose for orchestration
- **Cost:** $0

### Staging/Testing Stage
- Groq free tier for LLM
- Supabase free tier for database
- Upstash free tier for Redis
- Qdrant (Docker)
- Mailgun free tier for email
- Fly.io free tier for hosting
- **Cost:** $0 (within limits)

### Production Stage (Small)
- Groq or OpenAI for LLM
- Supabase Pro or self-hosted PostgreSQL
- Self-hosted Redis
- Self-hosted Qdrant
- Mailgun or Brevo for email
- Self-hosted on VPS or Fly.io
- Prometheus + Grafana for monitoring
- **Cost:** $50-100/month

### Production Stage (Large)
- OpenAI or Anthropic for LLM
- Self-hosted PostgreSQL cluster
- Self-hosted Redis cluster
- Self-hosted Qdrant cluster
- SendGrid for email
- Kubernetes cluster (K3s or managed)
- Full monitoring stack
- **Cost:** $200-500/month

---

## Installation & Setup

### Quick Start (100% Free, Local Development)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3

# 2. Clone and setup project
git clone <your-repo>
cd vendor-risk-tower

# 3. Start infrastructure with Docker Compose
docker-compose up -d

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Install frontend dependencies
cd frontend
npm install

# 6. Run backend
cd ..
uvicorn main:app --reload

# 7. Run frontend
cd frontend
npm run dev
```

### Docker Compose (Free Stack)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: vendor_risk
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana


