# CareerPilot — Comprehensive Project Overview

> **For NotebookLM:** This document covers the full architecture, technology stack, data flows, and design decisions behind CareerPilot — an AI-powered career guidance platform. Use this as the primary source for generating slide decks and audio overviews.

---

## 1. What is CareerPilot?

CareerPilot is a full-stack AI career intelligence platform that helps job seekers go from "I have a resume" to "I'm interview-ready and applying smart." It combines large language models, vector semantic search, intelligent agents, and browser automation into a seamless end-to-end experience.

**Core capabilities:**
- Upload a resume and get an instant AI-powered analysis with a score, grade, and actionable feedback
- Match your profile against real, live job postings with semantic match scores
- Identify skills gaps and get personalized course recommendations
- Prepare for interviews with role-specific questions and AI-evaluated answers
- Track job applications on a Kanban board
- Auto-fill job application forms on portals like LinkedIn, Indeed, Naukri, and Glassdoor using browser automation
- Chat with an AI career coach that knows your resume

---

## 2. Technology Stack

### Backend
| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (Python 3.13) |
| LLM | Google Gemini 2.5 Flash |
| Agent Orchestration | LangChain 0.3 + LangGraph 0.6 |
| Vector Database | PostgreSQL 16 + pgvector extension |
| Embeddings | 768-dimensional skill embeddings (pgvector) |
| Resume Parsing | PyMuPDF4LLM (PDF → Markdown) + custom NLP pipeline |
| Browser Automation | Playwright 1.51 + Chromium (stealth mode) |
| Job Search | JSearch API (RapidAPI) + Tavily API (fallback) |
| Auth | JWT Bearer tokens (optional, graceful fallback) |
| Server | Uvicorn ASGI |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15.5 (App Router, React 19) |
| UI Components | shadcn/ui (Radix UI primitives) |
| Styling | Tailwind CSS 4 |
| State & Caching | TanStack React Query v5 |
| Data Visualization | Recharts |
| Animations | Framer Motion |
| Persistence | localStorage-backed React Query cache |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 with pgvector |
| Containerization | Docker + Docker Compose |
| Services | 3 containers: PostgreSQL, FastAPI, Next.js |

---

## 3. System Architecture

CareerPilot is a **monorepo** containing two independently deployable services, orchestrated together via Docker Compose.

```
CareerPilot/
├── backend/          # FastAPI service (Python 3.13)
│   ├── src/app/
│   │   ├── api/v1/       # 12 route modules
│   │   ├── services/     # Business logic
│   │   ├── infrastructure/
│   │   │   ├── database/ # Models, repositories, migrations
│   │   │   └── rag/      # Embeddings service
│   │   ├── middleware/   # Auth, logging, error handling
│   │   └── schemas/      # Pydantic models
│   ├── Dockerfile
│   └── compose.yaml
├── frontend/         # Next.js app
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   ├── components/   # React components
│   │   ├── hooks/        # React Query hooks
│   │   ├── lib/          # API client, utilities
│   │   └── types/        # TypeScript types
│   ├── Dockerfile
│   └── compose.yaml
└── compose.yaml      # Root orchestration
```

---

## 4. AI & Agent Architecture

### 4.1 LangGraph-Powered Analysis Agent

The analysis pipeline is built on **LangGraph**, which defines a stateful, multi-step agent graph. Rather than calling the LLM once, the agent traverses a graph of nodes — each responsible for a specific analysis task — with state persisted across steps.

**Agent Graph Nodes:**
1. **ResumeLoader Node** — Fetches parsed resume profile from the database
2. **StrengthsAnalysis Node** — Uses Gemini to identify key resume strengths
3. **ImprovementSuggestions Node** — Generates targeted improvement recommendations
4. **MetricsExtraction Node** — Extracts quantitative metrics (years of experience, skill count, project count)
5. **ScoreAggregation Node** — Computes overall score (0–100), grade (A–F), and section breakdown
6. **OutputFormatting Node** — Structures results for the API response

LangGraph manages the control flow between these nodes, handles conditional branching (e.g., skip enrichment if resume is already high quality), and maintains a shared state object throughout the graph traversal.

**LangChain Tools used by the agent:**

| Tool | Purpose |
|------|---------|
| `analyze_resume_strengths_tool` | Identify top strengths using Gemini Vision |
| `suggest_improvements_tool` | Generate prioritized improvement list |
| `get_resume_metrics_tool` | Extract quantitative resume metrics |
| `recommend_courses_tool` | Suggest learning paths based on skills gap |
| `recommend_courses_with_context_tool` | Context-aware course recommendations |
| `get_contact_info` | Extract structured contact information |
| `get_skills` | Parse and categorize skills |
| `get_experience` | Extract work experience entries |
| `get_education` | Extract education history |
| `get_projects` | Extract project details |
| `get_achievements` | Extract achievements and awards |

**Memory:** A `ConversationMemory` module persists chat history within LangChain, enabling multi-turn conversations where the AI remembers earlier context.

### 4.2 Vector Embeddings & Semantic Search

Every resume processed by CareerPilot generates a **768-dimensional skill embedding vector** stored in PostgreSQL via the pgvector extension.

**How it works:**
1. After resume parsing, skills are extracted and aggregated into a text representation
2. The `EmbeddingsService` (`infrastructure/rag/embeddings/service.py`) encodes this text using Google's embedding model into a 768-dim vector
3. The vector is stored in `resume_profiles.skills_embedding` (a pgvector `VECTOR(768)` column)
4. At query time, job descriptions or target role requirements are also embedded into the same vector space
5. PostgreSQL performs **cosine similarity search** using pgvector's `<=>` operator to rank jobs by semantic relevance to the candidate's skill profile

**Why this matters:** Traditional keyword matching misses synonyms and related concepts. A resume listing "PyTorch" should match a job requiring "deep learning frameworks" — vector search handles this naturally.

**pgvector schema:**
```sql
skills_embedding VECTOR(768)  -- in resume_profiles table
-- Query example:
SELECT * FROM resume_profiles
ORDER BY skills_embedding <=> query_embedding
LIMIT 10;
```

### 4.3 RAG Pipeline for Career Guidance

The chat and career path features use a **Retrieval-Augmented Generation (RAG)** pattern:
1. User's resume profile is chunked and embedded
2. Relevant sections are retrieved based on the user's query
3. Retrieved context is injected into the LLM prompt alongside the question
4. Gemini generates a grounded, resume-specific answer

This ensures the AI career coach gives advice specific to *this* candidate's background, not generic career advice.

---

## 5. Resume Processing Pipeline

The resume pipeline is a multi-stage NLP system that transforms a raw PDF into structured, queryable data.

```
PDF / Markdown Upload
        ↓
┌─────────────────────────────────┐
│        ResumeProcessor          │
│  ┌─────────────────────────┐    │
│  │  PDF Detection          │    │
│  │  PyMuPDF4LLM →Markdown  │    │
│  └──────────┬──────────────┘    │
│             ↓                   │
│  ┌─────────────────────────┐    │
│  │     TextCleaner         │    │
│  │  Normalize whitespace   │    │
│  │  Remove artifacts       │    │
│  └──────────┬──────────────┘    │
│             ↓                   │
│  ┌─────────────────────────┐    │
│  │    SectionSplitter      │    │
│  │  Identify sections      │    │
│  │  (Contact, Skills, etc) │    │
│  └──────────┬──────────────┘    │
│             ↓                   │
│  ┌─────────────────────────┐    │
│  │  Structured Parsers     │    │
│  │  ExperienceParser       │    │
│  │  EducationParser        │    │
│  │  SkillsParser           │    │
│  └──────────┬──────────────┘    │
│             ↓                   │
│  ┌─────────────────────────┐    │
│  │  LLM Enrichment Layer   │    │
│  │  (Gemini Vision)        │    │
│  │  Validate, fill gaps    │    │
│  │  Extract insights       │    │
│  └──────────┬──────────────┘    │
└────────────-┼───────────────────┘
             ↓
    Structured JSON stored in
    resume_profiles.raw_data
    + skills_embedding (pgvector)
```

**Parsed sections:** contact info, skills (categorized), work experience (with dates, roles, bullets), education, projects (with tech stacks), achievements, co-curricular activities.

**Async architecture:** Processing is non-blocking. The API immediately returns a `job_id`, and the frontend polls `/resume/jobs/{job_id}` until status is `completed`. This prevents timeouts on large PDFs.

---

## 6. Database Schema

**PostgreSQL 16 + pgvector — 10 tables:**

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | User accounts | `id` (UUID), `email`, timestamps |
| `resume_profiles` | Parsed resumes + embeddings | `raw_data` (JSON), `skills_embedding` (VECTOR 768) |
| `conversations` | Chat sessions | `id`, `user_id`, `title` |
| `messages` | Chat messages | `role` (user/assistant/system), `content` |
| `analysis_history` | Analysis snapshots | `overall_score`, `grade`, `section_scores_json` |
| `user_sessions` | Active sessions | `profile_id`, `is_active`, `last_accessed_at` |
| `resume_processing_jobs` | Async job tracking | `status` (queued/processing/completed/failed), `progress` |
| `job_applications` | Application tracker | `company`, `status` (applied/interviewing/offer/rejected) |
| `portal_sessions` | Saved browser sessions | `portal`, `storage_state` (cookies + localStorage JSON) |
| `recommendation_feedback` | User feedback | `item_type` (job/course), `is_helpful` |

**Repository Pattern:** Each table has a dedicated repository class (`UserRepository`, `ResumeRepository`, etc.) that abstracts all database operations, keeping services clean of SQL.

---

## 7. API Routes

**Base URL:** `http://localhost:8000`

| Route Prefix | Description | Notable Endpoints |
|-------------|-------------|-------------------|
| `/resume` | Resume management | `POST /upload/async`, `GET /jobs/{job_id}` |
| `/analysis` | AI analysis | `/overview`, `/ats-score`, `/skills-gap`, `/job-match`, `/career-path` |
| `/jobs` | Job recommendations | `/recommendations`, `/salary-insights`, `/keywords` |
| `/chat` | AI conversation | `GET /stream` (SSE), `/history` |
| `/applications` | Application tracking | CRUD + `POST /auto-fill`, `GET /auto-fill/{task_id}` |
| `/interview` | Interview prep | `/questions`, `/evaluate` |
| `/agent` | Direct agent | `POST /query` |
| `/sessions` | Session management | CRUD |
| `/courses` | Course recommendations | `/recommendations` |
| `/progress` | Progress tracking | Progress endpoints |
| `/feedback` | Recommendation feedback | CRUD |
| `/` | Health | `GET /health` |

---

## 8. Frontend Architecture

### Page Structure (Next.js App Router)

```
/                          → Landing page (resume upload)
/dashboard/
  ├── overview/            → Score card, metrics, ATS highlights, charts
  ├── jobs/                → Job recommendations with match scores
  ├── chat/                → AI career coach (streaming chat)
  ├── applications/        → Kanban board + auto-fill
  ├── interview/           → Question bank + AI evaluation
  ├── skills/              → Skills breakdown + gap analysis
  └── career/              → Career path milestones
```

### React Query + localStorage Persistence

All API data is cached in React Query with a custom localStorage persister:
- On resume upload success, **all dashboard data is prefetched** (analysis, jobs, career path, interview questions, courses) before navigating to the dashboard
- On subsequent visits, data loads **instantly** from localStorage — no loading spinners
- Cache is keyed by `user_id` and `profile_id` stored in localStorage after upload

### Streaming Chat (SSE)

Chat messages stream token-by-token via Server-Sent Events:
```
Frontend opens EventSource → GET /chat/stream?message=...
Backend yields:
  { event: "meta",  data: { model, timestamp } }
  { event: "token", data: "Hello" }
  { event: "token", data: " there" }
  { event: "end",   data: { total_tokens } }
Frontend accumulates tokens → live typing effect in UI
```

---

## 9. Playwright Browser Automation

One of CareerPilot's most innovative features is its **stealth browser automation** for job application auto-fill.

### How it works:
1. User clicks "Auto-Fill" on a job application and provides the job portal URL
2. Backend creates a background task and returns a `task_id` immediately
3. Playwright launches a **stealth Chromium browser** with:
   - `navigator.webdriver` spoofed to `false`
   - Randomized browser fingerprint (viewport, user-agent, timezone)
   - Human-like mouse movements and typing delays
4. The browser navigates to the job portal (LinkedIn, Indeed, Naukri, Glassdoor, or DemoQA)
5. **Gemini Vision** analyzes a screenshot of the form to identify field labels and types
6. Form fields are filled using resume data (name, email, phone, experience, skills)
7. Screenshots are captured at each step
8. Browser session (cookies + localStorage) is saved in `portal_sessions` for reuse — the user doesn't need to log in again

### Live Progress Updates:
The frontend polls every 2 seconds and displays:
- Step-by-step timeline with icons and status messages
- Expandable screenshots of each automation step
- Overall progress percentage

### Supported Portals:
- LinkedIn
- Indeed
- Naukri
- Glassdoor
- DemoQA (for testing)

---

## 10. Key Data Flows

### Flow 1: Resume Upload → Analysis

```
1. User drags & drops PDF onto landing page
2. POST /resume/upload/async?enrich=true (FormData)
3. Backend: PDF → Markdown → Clean → Parse → Enrich (Gemini) → Store
4. Frontend polls GET /resume/jobs/{job_id} every 1.5s
5. On completion:
   - Saves user_id, profile_id to localStorage
   - Prefetches all dashboard data in parallel
   - Navigates to /dashboard/overview
6. Dashboard renders instantly from prefetched cache
```

### Flow 2: Semantic Job Matching

```
1. GET /jobs/recommendations?user_id=...
2. Load resume profile + skills_embedding from DB
3. Query JSearch API for real job postings
4. Embed each job description → 768-dim vector
5. Compute cosine similarity: job_vector <=> resume_embedding
6. Rank and filter by match score
7. Return top N jobs with match percentages
```

### Flow 3: LangGraph Analysis Pipeline

```
1. GET /analysis/overview?user_id=...
2. LangGraph initializes agent state with resume profile
3. Graph traversal:
   Node 1: Load resume → shared state
   Node 2: Strengths analysis (Gemini)   ─┐
   Node 3: Improvements (Gemini)          ├─ parallel execution
   Node 4: Metrics extraction (Gemini)   ─┘
   Node 5: Aggregate → score + grade
   Node 6: Format response
4. Return: { score, grade, strengths, weaknesses, improvements, section_scores }
```

### Flow 4: Auto-Fill Task

```
1. POST /applications/auto-fill { url, portal, user_id }
2. Returns task_id immediately (non-blocking)
3. Background Playwright task:
   ├── Load saved portal_session (cookies)
   ├── Navigate to job URL
   ├── Screenshot → Gemini Vision → identify fields
   ├── Fill fields with resume data
   ├── Screenshot after each field
   └── Update task progress in DB
4. Frontend polls every 2s → live step timeline with screenshots
5. On completion → option to submit or review
```

---

## 11. Third-Party Integrations

| Integration | Purpose | Notes |
|-------------|---------|-------|
| **Google Gemini 2.5 Flash** | LLM for all AI features — analysis, enrichment, chat, vision | Primary intelligence layer |
| **LangChain 0.3** | Agent framework, prompt templates, tool execution, memory | Orchestrates multi-step reasoning |
| **LangGraph 0.6** | Stateful multi-step agent graphs with conditional branching | Powers the analysis pipeline |
| **pgvector** | 768-dim vector storage and cosine similarity search in PostgreSQL | Enables semantic job matching |
| **Playwright + Chromium** | Headless browser automation for job portal auto-fill | Stealth mode to bypass bot detection |
| **Tavily API** | Web search for job recommendations (fallback) | Searches the live web for job postings |
| **JSearch API (RapidAPI)** | Real-time job postings from Indeed and other boards | Primary job data source |
| **PyMuPDF4LLM** | PDF to Markdown conversion for resume parsing | Preserves structure better than plain text extraction |
| **shadcn/ui** | Accessible, customizable React component library | Built on Radix UI primitives |
| **TanStack React Query v5** | Data fetching, caching, background sync | With localStorage persistence layer |
| **Recharts** | Data visualization (bar charts, radar charts, gauges) | Used for skills breakdown and section scores |
| **Framer Motion** | Smooth UI animations and transitions | Used on landing page and dashboard |

---

## 12. Deployment Architecture

### Docker Compose (3 Services)

```yaml
Services:
  db:       pgvector/pgvector:pg16
            Port: 5432
            Volume: postgres_data (persistent)
            Health: pg_isready check

  api:      python:3.13-slim
            Port: 8000
            Includes: Playwright + Chromium pre-installed
            Depends on: db (healthy)
            CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend: node:20-alpine (multi-stage build)
            Port: 3000
            Build: npm run build → Next.js standalone
            CMD: node server.js
```

### Environment Variables (Backend)
| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Google Gemini API access |
| `TAVILY_API_KEY` | Tavily web search |
| `JSEARCH_API_KEY` | RapidAPI JSearch |
| `DATABASE_URL` | PostgreSQL connection string |
| `MODEL_NAME` | Gemini model override (default: gemini-2.5-flash) |
| `JWT_SECRET` | JWT signing key (optional) |

### Local URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |

---

## 13. Notable Design Patterns

| Pattern | Where Used | Why |
|---------|-----------|-----|
| **LangGraph State Machine** | Analysis pipeline | Structured multi-step reasoning with shared state |
| **Vector Similarity Search** | Job matching | Semantic relevance beyond keyword matching |
| **RAG (Retrieval-Augmented Generation)** | Chat, career path | Grounds LLM responses in the user's actual resume |
| **Async Task Queue** | Resume processing, auto-fill | Non-blocking — returns job_id, frontend polls for progress |
| **Repository Pattern** | All DB access | Decouples business logic from SQL |
| **Service Layer** | Business logic | Thin API routes, fat services |
| **SSE Streaming** | Chat, progress updates | Real-time output without WebSocket complexity |
| **React Query + localStorage** | Frontend caching | Instant load times, offline resilience |
| **Stealth Browser Automation** | Job portal auto-fill | Fingerprint spoofing to bypass bot detection |
| **Graceful Degradation** | Auth, API keys | App works even if optional services are missing |

---

## 14. What Makes CareerPilot Unique

1. **End-to-end AI pipeline** — from raw PDF to scored analysis to live job matches to auto-filled applications, all in one platform

2. **Semantic skill matching with pgvector** — 768-dimensional skill embeddings enable nuanced job-to-resume matching that keyword search cannot achieve

3. **LangGraph-driven analysis** — stateful agent graphs enable structured, multi-step analysis with conditional branching rather than a single monolithic LLM call

4. **Live job data** — integrates with real job APIs (JSearch, Tavily) so recommendations reflect actual openings, not static datasets

5. **Browser automation with Gemini Vision** — Playwright automation is guided by Gemini Vision analyzing screenshots, making it adaptable to any portal layout without hardcoded selectors

6. **Persistent portal sessions** — saves browser cookies so users stay logged in across auto-fill sessions

7. **Instant dashboard loads** — aggressive prefetching on upload + localStorage cache means the dashboard renders immediately with no loading states

8. **Full-stack type safety** — Pydantic models on the backend, TypeScript interfaces on the frontend, both generated from the same data contract

---

## 15. Summary

CareerPilot is a production-grade AI platform that combines:

- **LangGraph + LangChain** for structured, multi-step AI agent reasoning
- **Google Gemini 2.5 Flash** as the intelligence backbone (text + vision)
- **pgvector semantic search** for nuanced, embedding-based job matching
- **RAG pipeline** for grounded, resume-specific career advice
- **Playwright stealth automation** for hands-free job application form filling
- **Next.js + React Query** for a fast, cached, responsive frontend
- **FastAPI + PostgreSQL** for a scalable, async-first backend
- **Docker Compose** for one-command local deployment

The platform demonstrates how modern AI primitives — LLMs, vector databases, agent frameworks, and browser automation — can be combined into a cohesive, genuinely useful product that solves a real problem for job seekers.
