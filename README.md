## CareerPilot

CareerPilot is an AI-assisted career platform: upload a resume, get analysis and job matching, track applications, prepare for interviews, and (on supported portals) run browser-based application auto-fill with optional saved portal sessions.

The repo is a **monorepo** with a FastAPI backend and a Next.js (App Router) frontend, orchestrated via Docker Compose.

### Tech stack

| Area | Technology |
|------|-------------|
| Backend | FastAPI (Python 3.13), Uvicorn, LangChain / LangGraph, Google Gemini |
| Data | PostgreSQL 16 + pgvector, SQLAlchemy |
| Automation | Playwright (Chromium), Gemini Vision for form interaction |
| Jobs / search | Tavily (and related APIs per deployment; see `backend/.env.local`) |
| Frontend | Next.js 15, React 19, TanStack Query, shadcn/ui, Tailwind CSS 4 |
| Tooling | `uv` (Python), `ruff`; Node package manager of your choice in `frontend/` |

### Repository layout

- `backend/` — API, agents, RAG/embeddings, Playwright automation, database layer  
- `frontend/` — Next.js UI (dashboard, resume flow, jobs, applications, interview prep)  
- `compose.yaml` — root Compose file that includes `backend/compose.yaml` and `frontend/compose.yaml`

### What the app does (high level)

- Resume upload (PDF or text) → structured profile stored in PostgreSQL  
- Analysis: overview, skills gap, career path; streaming chat with history  
- ATS-style scoring against a pasted job description  
- Job recommendations and role match scoring  
- Application tracker (CRUD + stats) with Kanban-style UI  
- Auto-fill tasks for supported job portals (async tasks, progress polling, screenshots)  
- Portal session import / login helpers so automation can reuse signed-in state  
- Interview question flow and answer evaluation  
- Optional JWT auth; most flows key off `user_id` query param as documented in the API  

Use OpenAPI at `http://localhost:8000/docs` when the API is running for routes, schemas, and try-it-out requests.

### Quickstart with Docker

From the repository root (Docker Desktop or compatible engine required):

```bash
docker compose up --build
```

Typical service layout after `up`:

| Service | Port |
|---------|------|
| PostgreSQL (pgvector) | 5432 |
| FastAPI | 8000 |
| Next.js (production image) | 3000 |

**Before `docker compose up`:** create `backend/.env.local` (Compose requires this file). Copy the template and add keys:

```bash
cp backend/.env.example backend/.env.local
```

The API reads `GOOGLE_API_KEY` and `TAVILY_API_KEY` at startup (both are required by the backend settings model). Edit `backend/.env.local` with real values.

### Quickstart (local development)

**Backend** (recommended: `uv`):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

- App: `http://localhost:3000`  
- API docs: `http://localhost:8000/docs`  
- The frontend defaults `NEXT_PUBLIC_API_URL` to `http://localhost:8000` (see `frontend/src/lib/config.ts`). Override if your API is on another host/port.

### Environment variables

Configure `backend/.env.local` (never commit secrets; the file is gitignored). **Required for the app to boot:** `GOOGLE_API_KEY`, `TAVILY_API_KEY` (see `backend/.env.example` for placeholders and optional variables).

Also common:

- `DATABASE_URL` — when not using Compose defaults, point at your Postgres instance (SQLAlchemy URL)  
- `MODEL_NAME` — e.g. `gemini-2.5-flash` (see `backend/README.md` for allowed values)  
- `JSEARCH_API_KEY` — optional RapidAPI JSearch integration  

Docker Compose sets `DATABASE_URL` for the `api` service to the bundled `db` service. For model options and backend troubleshooting, see `backend/README.md`.

### Useful links

- `backend/README.md` — backend env, run commands, linting  
- `frontend/README.md` — Next.js dev server notes  
- `IEEEpaper.pdf` — academic paper for the project (code in this repo is separate from the paper’s license; clarify reuse with the authors if needed)

### Visitor / demo notes

- **Default Postgres password** in Compose is `postgres` / `postgres` — fine for local demos, not for public deployments.  
- **CORS** defaults to permissive settings in config; tighten `CORS_ORIGINS` for any shared or production host.  
- **Auto-fill** uses headless browser automation against third-party sites; terms of use and consent are the operator’s responsibility.  
- There is **no `LICENSE` file** yet; add one (for example MIT or Apache-2.0) if you want others to know how they may use the code.
