# Final Technology Stack - Vendor Risk Control Tower

## Complete Technology Stack (100% Free)

This is the finalized technology stack for building the multi-agent vendor risk assessment system with all free and open-source components.

--

## Core Backend Stack

### Application Framework
**FastAPI** (Free, MIT License)
- Modern Python web framework
- Async support built-in
- Automatic OpenAPI documentation
- High performance
- Type hints support

### Programming Language
**Python 3.11+** (Free, PSF License)
- Excellent AI/ML ecosystem
- LangChain/LangGraph support
- Rich library ecosystem
- Type safety with type hints

---

## LLM & AI Stack

### LLM Provider

**Primary: Ollama (100% Free, Self-Hosted)**
- Run LLMs locally on your machine
- Zero API costs
- Complete privacy and data control
- Recommended models:
  - **llama3.1:8b** - Best balance of performance and speed
  - **llama3.1:70b** - Better reasoning (requires more resources)
  - **mistral:7b** - Fast and efficient
  - **mixtral:8x7b** - Excellent for complex reasoning
- Installation: `curl -fsSL https://ollama.com/install.sh | sh`
- GPU support: CUDA, ROCm, Metal (Apple Silicon)
- CPU fallback: Works on CPU but slower

**Fallback: Groq (Free Tier)**
- Fast inference (fastest LLM API)
- Free tier: Generous rate limits
- Available models:
  - llama-3.1-70b-versatile
  - llama-3.1-8b-instant
  - mixtral-8x7b-32768
- Use when: Ollama is down or needs faster response
- API key: Free at console.groq.com

**LLM Configuration Strategy:**
```python
# Primary: Ollama
primary_llm = ChatOllama(
    model="llama3.1:8b",
    base_url="http://localhost:11434",
    temperature=0
)

# Fallback: Groq
fallback_llm = ChatGroq(
    model="llama-3.1-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# Automatic fallback
llm = primary_llm.with_fallbacks([fallback_llm])
```

### Agent Framework
**LangChain** (Free, MIT License)
- Tool integration and management
- Agent creation and orchestration
- Prompt management and templates
- Memory and state management
- Ollama integration built-in

**LangGraph** (Free, MIT License)
- Multi-agent orchestration
- State machine management
- Parallel execution support
- Checkpointing and persistence
- Built on top of LangChain

### Embeddings

**Sentence Transformers (100% Free, Self-Hosted)**

**Primary Model: all-MiniLM-L6-v2**
- Dimensions: 384
- Speed: Very fast
- Quality: Good for most use cases
- Memory: Low footprint
- Use for: Policy search, document classification

**Secondary Model: all-mpnet-base-v2**
- Dimensions: 768
- Speed: Moderate
- Quality: Better semantic understanding
- Memory: Moderate footprint
- Use for: Complex semantic search, similarity matching

**Installation:**
```python
from sentence_transformers import SentenceTransformer

# Load models locally
model_mini = SentenceTransformer('all-MiniLM-L6-v2')
model_mpnet = SentenceTransformer('all-mpnet-base-v2')
```

**Benefits:**
- Run locally, no API costs
- No rate limits
- Complete privacy
- Fast inference
- Good quality embeddings

---

## Database Stack

### Primary Database
**Supabase (Free Tier)**
- PostgreSQL 15+ database
- Free tier includes:
  - 500MB database storage
  - 2GB bandwidth per month
  - Unlimited API requests
  - 50MB file storage
- Built-in features:
  - Realtime subscriptions
  - Row Level Security (RLS)
  - Auto-generated REST API
  - Auto-generated GraphQL API
  - Built-in authentication
  - Storage for documents
- Dashboard: Easy database management
- Backup: Automatic daily backups
- Connection: Direct PostgreSQL connection or REST API

**Why Supabase:**
- Free tier is generous
- PostgreSQL with modern features
- Built-in file storage for documents
- Realtime updates for frontend
- Easy to scale when needed

**Connection Options:**
```python
# Option 1: Direct PostgreSQL connection
import psycopg2
conn = psycopg2.connect(
    host="db.xxx.supabase.co",
    database="postgres",
    user="postgres",
    password="your-password"
)

# Option 2: Supabase Python client
from supabase import create_client
supabase = create_client(
    "https://xxx.supabase.co",
    "your-anon-key"
)
```

### Caching & State Management
**Redis (Free, Self-Hosted)**
- In-memory data store
- Fast caching layer
- Session management
- Pub/sub for real-time updates
- State persistence for agents

**Deployment:**
- Docker: `docker run -d -p 6379:6379 redis:7`
- Or use Redis Cloud free tier (30MB)

**Usage:**
- Cache policy search results (1 hour TTL)
- Cache external API responses (24 hour TTL)
- Store active agent state
- Pub/sub for real-time frontend updates

---

## Vector Database

**Qdrant (100% Free, Self-Hosted, Apache 2.0)**
- Open-source vector database
- Excellent performance
- REST API and gRPC
- Web UI included at http://localhost:6333/dashboard
- Filtering and metadata support
- Snapshots and backups

**Deployment:**
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

**Collections:**
- `security_policies` - Security policy embeddings (384 dimensions)
- `compliance_policies` - Compliance policy embeddings (384 dimensions)
- `financial_policies` - Financial policy embeddings (384 dimensions)

**Why Qdrant:**
- Free and open-source
- Better performance than Chroma
- Production-ready
- Easy Docker deployment
- Good Python client
- Web UI for debugging

---

## Document Processing

### PDF Processing
**pdfplumber** (Free, MIT License)
- Better text extraction than PyPDF2
- Table extraction support
- Layout analysis
- Bounding box information
- Character-level precision

**Installation:**
```bash
pip install pdfplumber
```

**Usage:**
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
```

### Word Documents
**python-docx** (Free, MIT License)
- Read/write DOCX files
- Extract text and formatting
- Table extraction
- Paragraph and style access

### Excel Files
**openpyxl** (Free, MIT License)
- Read/write XLSX files
- Formula support
- Multiple sheets
- Cell formatting

**pandas** (Free, BSD License)
- Data manipulation
- Excel reading with `pd.read_excel()`
- CSV support

### OCR (Optical Character Recognition)
**EasyOCR** (Free, Apache 2.0)
- Deep learning-based OCR
- Better accuracy than Tesseract
- 80+ language support
- GPU acceleration support
- Easy to use

**Installation:**
```bash
pip install easyocr
```

**Usage:**
```python
import easyocr
reader = easyocr.Reader(['en'])
result = reader.readtext('scanned_document.jpg')
```

---

## Email Service

**Mailgun (Free Tier)**
- 5,000 emails per month free
- Good deliverability
- Email tracking and analytics
- Email validation API
- Webhook support
- Multiple domains

**Why Mailgun:**
- Generous free tier (5,000/month)
- Better deliverability than Gmail SMTP
- Professional email service
- Easy API integration
- Email templates support

**Setup:**
```python
import requests

def send_email(to, subject, body):
    return requests.post(
        "https://api.mailgun.net/v3/YOUR_DOMAIN/messages",
        auth=("api", "YOUR_API_KEY"),
        data={
            "from": "Vendor Risk <noreply@yourdomain.com>",
            "to": to,
            "subject": subject,
            "html": body
        }
    )
```

**Alternative for Development:**
- Gmail SMTP (free, 500 emails/day)
- Use for local testing

---

## External APIs

### Company Information

**Primary: Mock Service (100% Free)**
- Create mock credit rating service
- Realistic test data
- Use for development and demo
- No API costs

**Secondary: OpenCorporates API (Free)**
- Company information lookup
- Basic company data
- Free tier available
- Rate limited but sufficient
- Good for real company validation

**Usage:**
```python
import requests

def get_company_info(company_name):
    # OpenCorporates API
    response = requests.get(
        f"https://api.opencorporates.com/v0.4/companies/search",
        params={"q": company_name}
    )
    return response.json()
```

### Breach Data

**Internal Breach Database (100% Free)**
- Build from public breach sources
- Scrape from:
  - HaveIBeenPwned breach list (public)
  - Public breach disclosures
  - Security news sources
- Store in PostgreSQL
- Update monthly
- No API costs
- No rate limits

**Database Schema:**
```sql
CREATE TABLE breaches (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    domain VARCHAR(255),
    breach_date DATE,
    records_exposed INTEGER,
    data_types TEXT[],
    severity VARCHAR(50),
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Alternative:**
- HaveIBeenPwned API (free but rate limited)
- Use as fallback or validation

### Security Scanning

**SSL Labs API (Free)**
- SSL/TLS testing
- Certificate validation
- Security grade (A+ to F)
- Free to use
- Rate limited (1 request per 10 seconds)

**Usage:**
```python
import requests
import time

def scan_ssl(domain):
    # Start scan
    requests.get(
        "https://api.ssllabs.com/api/v3/analyze",
        params={"host": domain, "startNew": "on"}
    )
    
    # Wait for completion
    time.sleep(30)
    
    # Get results
    response = requests.get(
        "https://api.ssllabs.com/api/v3/analyze",
        params={"host": domain}
    )
    return response.json()
```

**Additional Free Security Checks:**
- SecurityHeaders.com API (free)
- Mozilla Observatory API (free)
- Manual checks: SSL version, cipher suites, security headers

---

## Frontend Stack

### Framework & Build Tool
**React 18** (Free, MIT License)
- Modern UI library
- Component-based architecture
- Hooks for state management
- Large ecosystem

**Vite** (Free, MIT License)
- Lightning-fast build tool
- Hot Module Replacement (HMR)
- Optimized production builds
- Better than Create React App
- TypeScript support out of the box

**Project Setup:**
```bash
npm create vite@latest vendor-risk-frontend -- --template react-ts
```

### Language
**TypeScript** (Free, Apache 2.0)
- Type safety
- Better IDE support
- Fewer runtime errors
- Better refactoring
- Industry standard

### Styling
**TailwindCSS** (Free, MIT License)
- Utility-first CSS framework
- Fast development
- Responsive design built-in
- Small production bundle
- Highly customizable

**Installation:**
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### UI Component Library
**shadcn/ui** (Free, MIT License)
- Beautiful, accessible components
- Built on Radix UI primitives
- Copy-paste components (not npm package)
- Fully customizable
- TailwindCSS-based
- Components include:
  - Button, Card, Dialog, Dropdown
  - Table, Tabs, Toast, Form
  - Chart, Badge, Avatar, etc.

**Why shadcn/ui:**
- Not a dependency (copy components)
- Full control over code
- Beautiful default styling
- Accessible (ARIA compliant)
- TypeScript support

**Setup:**
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card table
```

### State Management
**Zustand** (Free, MIT License)
- Simple and lightweight
- No boilerplate
- TypeScript support
- DevTools support
- Easy to learn

**Usage:**
```typescript
import create from 'zustand'

const useStore = create((set) => ({
  vendors: [],
  addVendor: (vendor) => set((state) => ({ 
    vendors: [...state.vendors, vendor] 
  }))
}))
```

### Server State Management
**TanStack Query (React Query)** (Free, MIT License)
- Server state management
- Automatic caching
- Background refetching
- Optimistic updates
- Pagination support
- Excellent DevTools

**Why React Query:**
- Handles all API data fetching
- Automatic cache invalidation
- Loading and error states
- Retry logic built-in

### Routing
**React Router v6** (Free, MIT License)
- Client-side routing
- Nested routes
- Lazy loading
- TypeScript support

### Forms
**React Hook Form** (Free, MIT License)
- Performant form handling
- Easy validation
- TypeScript support
- Small bundle size
- Works great with shadcn/ui

**Zod** (Free, MIT License)
- TypeScript-first schema validation
- Runtime type checking
- Integrates with React Hook Form

### Charts & Visualization
**Recharts** (Free, MIT License)
- React chart library
- Responsive charts
- Customizable
- Good documentation
- Components:
  - Line, Bar, Pie, Area charts
  - Radar, Scatter, Composed charts
  - Responsive containers

**Usage:**
```typescript
import { LineChart, Line, XAxis, YAxis } from 'recharts'

<LineChart data={data}>
  <XAxis dataKey="name" />
  <YAxis />
  <Line type="monotone" dataKey="score" stroke="#8884d8" />
</LineChart>
```

### Icons
**Lucide React** (Free, ISC License)
- Beautiful, consistent icons
- Tree-shakeable (only import what you use)
- 1000+ icons
- Customizable size and color

**Installation:**
```bash
npm install lucide-react
```

### Date Handling
**date-fns** (Free, MIT License)
- Modern date utility library
- Tree-shakeable
- TypeScript support
- Better than Moment.js

### File Upload
**react-dropzone** (Free, MIT License)
- Drag-and-drop file upload
- File type validation
- Multiple file support
- Preview support

### Real-Time Updates
**Socket.IO Client** (Free, MIT License)
- Real-time bidirectional communication
- Automatic reconnection
- Room support
- Fallback support

---

## Testing Stack

### Backend Testing
**pytest** (Free, MIT License)
- Python testing framework
- Fixtures and parametrization
- Excellent plugin ecosystem

**pytest-asyncio** (Free, Apache 2.0)
- Async test support

**pytest-cov** (Free, MIT License)
- Code coverage reporting

**httpx** (Free, BSD License)
- HTTP client for testing APIs
- Async support

### Frontend Testing
**Vitest** (Free, MIT License)
- Fast unit testing
- Vite-native (same config)
- Jest-compatible API
- Built-in coverage

**React Testing Library** (Free, MIT License)
- Component testing
- User-centric testing approach
- Accessibility-focused

**Playwright** (Free, Apache 2.0)
- E2E testing
- Cross-browser (Chrome, Firefox, Safari)
- Auto-wait for elements
- Screenshot and video recording
- Better than Selenium/Cypress

**Installation:**
```bash
npm install -D vitest @testing-library/react @playwright/test
```

### Load Testing
**Locust** (Free, MIT License)
- Python-based load testing
- Distributed testing
- Web UI for monitoring
- Easy to write tests

---

## Monitoring & Observability

### Metrics
**Prometheus** (Free, Apache 2.0)
- Time-series database
- Metrics collection
- Alerting rules
- Industry standard

**Deployment:**
```bash
docker run -d -p 9090:9090 \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### Dashboards
**Grafana** (Free, AGPL)
- Beautiful dashboards
- Multiple data sources
- Alerting
- Community dashboards
- Variables and templating

**Deployment:**
```bash
docker run -d -p 3000:3000 grafana/grafana
```

### Logging
**Loki + Promtail** (Free, AGPL)
- Log aggregation
- Integrates with Grafana
- Lightweight (better than ELK)
- Label-based indexing

**Why Loki:**
- Simpler than ELK stack
- Less resource-intensive
- Native Grafana integration
- Good for small to medium scale

### Tracing
**Jaeger** (Free, Apache 2.0)
- Distributed tracing
- OpenTelemetry compatible
- Web UI included
- Service dependency graph

**Deployment:**
```bash
docker run -d -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one
```

### Application Monitoring
**OpenTelemetry** (Free, Apache 2.0)
- Unified observability framework
- Metrics, logs, and traces
- Vendor-neutral
- Python and JavaScript SDKs

### Error Tracking
**Sentry (Free Tier)**
- 5,000 events per month free
- Error tracking
- Performance monitoring
- Release tracking
- Source maps support

**Alternative:**
- Self-hosted Sentry (100% free)

---

## Deployment & Infrastructure

### Containerization
**Docker** (Free, Apache 2.0)
- Container runtime
- Image building
- Consistent environments

**Docker Compose** (Free, Apache 2.0)
- Multi-container orchestration
- Perfect for development
- Easy configuration

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - qdrant
  
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### Container Orchestration
**K3s** (Free, Apache 2.0)
- Lightweight Kubernetes
- Perfect for small deployments
- Less resource-intensive than K8s
- Single binary
- Built-in load balancer

**Why K3s:**
- Production-ready
- Easy to install
- Low resource usage
- Full Kubernetes compatibility

**Installation:**
```bash
curl -sfL https://get.k3s.io | sh -
```

### Reverse Proxy / Load Balancer
**Traefik** (Free, MIT License)
- Modern reverse proxy
- Automatic HTTPS (Let's Encrypt)
- Kubernetes-native
- Docker integration
- Dashboard included

**Why Traefik:**
- Automatic service discovery
- Easy SSL certificate management
- Modern and actively maintained
- Great for microservices

### CI/CD
**GitHub Actions** (Free for public repos, 2,000 minutes/month for private)
- Integrated with GitHub
- Easy YAML configuration
- Matrix builds
- Artifact storage
- Secrets management

**Workflow Example:**
```yaml
name: CI/CD
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest
      - name: Build Docker image
        run: docker build -t app .
```

---

## Development Tools

### Code Editor
**VS Code** (Free, MIT License)
- Excellent Python/TypeScript support
- Extensions ecosystem
- Integrated terminal
- Git integration
- Remote development

**Essential Extensions:**
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Docker

### API Testing
**Insomnia** (Free, MIT License)
- API testing and debugging
- GraphQL support
- Environment variables
- Request collections
- Open source

**Alternative:** Postman (free tier)

### Database Management
**DBeaver** (Free, Apache 2.0)
- Universal database tool
- PostgreSQL support
- SQL editor with autocomplete
- ER diagrams
- Data export/import

**For Supabase:**
- Use Supabase Dashboard (web-based)
- Or connect DBeaver to Supabase PostgreSQL

### Version Control
**Git** (Free, GPL)
- Version control system
- Industry standard

**GitHub** (Free for public repos)
- Code hosting
- CI/CD (GitHub Actions)
- Issue tracking
- Pull requests
- Project boards

---

## Security

### Secrets Management
**Environment Variables** (Free)
- Use .env files for development
- Never commit secrets to Git
- Use .env.example for templates

**python-dotenv** (Free, BSD License)
```python
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
```

### Vulnerability Scanning
**Trivy** (Free, Apache 2.0)
- Container image scanning
- Dependency scanning
- Fast and accurate
- CI/CD integration

**Installation:**
```bash
# Scan Docker image
trivy image your-image:latest

# Scan dependencies
trivy fs .
```

### SSL Certificates
**Let's Encrypt** (Free)
- Free SSL certificates
- Automated renewal
- Trusted by all browsers

**Certbot** (Free, Apache 2.0)
- Let's Encrypt client
- Automatic renewal
- Nginx/Apache plugins

---

## Complete Stack Summary

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Database:** Supabase (PostgreSQL)
- **Cache:** Redis (self-hosted)
- **Vector DB:** Qdrant (self-hosted)

### AI/ML
- **Primary LLM:** Ollama (llama3.1:8b, self-hosted)
- **Fallback LLM:** Groq (llama-3.1-70b-versatile, free tier)
- **Agent Framework:** LangChain + LangGraph
- **Embeddings:** Sentence Transformers
  - all-MiniLM-L6-v2 (384d) - Primary
  - all-mpnet-base-v2 (768d) - Secondary

### Document Processing
- **PDF:** pdfplumber
- **Word:** python-docx
- **Excel:** openpyxl + pandas
- **OCR:** EasyOCR

### Frontend
- **Framework:** React 18 + Vite
- **Language:** TypeScript
- **Styling:** TailwindCSS
- **Components:** shadcn/ui
- **State:** Zustand (client) + React Query (server)
- **Routing:** React Router v6
- **Forms:** React Hook Form + Zod
- **Charts:** Recharts
- **Icons:** Lucide React

### External Services
- **Email:** Mailgun (5,000/month free)
- **Company Info:** Mock + OpenCorporates API (free)
- **Breach Data:** Internal database (free)
- **Security Scan:** SSL Labs API (free)

### Infrastructure
- **Containers:** Docker + Docker Compose
- **Orchestration:** K3s (for production)
- **Reverse Proxy:** Traefik
- **CI/CD:** GitHub Actions

### Monitoring
- **Metrics:** Prometheus
- **Dashboards:** Grafana
- **Logging:** Loki + Promtail
- **Tracing:** Jaeger
- **Errors:** Sentry (free tier)

### Testing
- **Backend:** pytest + pytest-asyncio + pytest-cov
- **Frontend:** Vitest + React Testing Library + Playwright
- **Load:** Locust

---

## Cost Breakdown

### 100% Free (Self-Hosted)
- **LLM:** Ollama (self-hosted) - $0
- **Database:** Supabase free tier - $0
- **Cache:** Redis (Docker) - $0
- **Vector DB:** Qdrant (Docker) - $0
- **Email:** Mailgun free tier - $0 (5,000/month)
- **Hosting:** Self-hosted - $0
- **Total:** $0/month

### With Fallback (Free Tiers)
- **LLM Primary:** Ollama - $0
- **LLM Fallback:** Groq free tier - $0
- **Database:** Supabase free tier - $0
- **Everything else:** Free
- **Total:** $0/month (within limits)

### Small Production (If Scaling Needed)
- **LLM:** Groq (pay-as-you-go) - ~$20-30/month
- **Database:** Supabase Pro - $25/month
- **Hosting:** VPS or cloud - $10-20/month
- **Total:** ~$55-75/month

---

## Quick Start

### 1. Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
```

### 2. Install Sentence Transformers
```bash
pip install sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### 3. Start Infrastructure
```bash
docker-compose up -d
```

### 4. Setup Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 5. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

### 6. Access Applications
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant UI: http://localhost:6333/dashboard
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

---

## Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key

# Redis
REDIS_URL=redis://localhost:6379

# Qdrant
QDRANT_URL=http://localhost:6333

# LLM
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=your-groq-api-key

# Email
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com

# External APIs
OPENCORPORATES_API_KEY=your-key (optional)
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

---

## Recommended Hardware

### Development
- **CPU:** 4 cores
- **RAM:** 8GB minimum (16GB recommended for Ollama)
- **Storage:** 20GB SSD
- **GPU:** Optional (speeds up Ollama)

### Production (Small Scale)
- **CPU:** 8 cores
- **RAM:** 16GB minimum (32GB recommended)
- **Storage:** 100GB SSD
- **GPU:** Optional but recommended for Ollama

### Ollama Performance
- **CPU only:** Works but slower (5-10 tokens/sec)
- **GPU (NVIDIA):** Much faster (50-100 tokens/sec)
- **Apple Silicon (M1/M2/M3):** Good performance (30-60 tokens/sec)

---

## Conclusion

This stack is 100% free for development and can handle production workloads with minimal costs. All components are:
- ✅ Free and open-source
- ✅ Production-ready
- ✅ Well-maintained
- ✅ Actively developed
- ✅ Good documentation
- ✅ Large community

**Total Cost to Get Started: $0**

**Estimated Monthly Cost (Production): $0-75**

You can run everything locally for free and scale up as needed!
