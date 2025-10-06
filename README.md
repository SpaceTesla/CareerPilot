## CareerPilot

CareerPilot is a capstone project focused on building a modern career assistant platform. The repository is a monorepo with a FastAPI backend and room for a future Next.js frontend.

### Tech stack

- **Backend**: FastAPI (Python 3.13), LangChain + Google Gemini, Uvicorn
- **Tooling**: `uv` for dependency management, `ruff` for linting
- **Frontend (planned)**: Next.js (TypeScript) + TailwindCSS

### Repository structure

- `backend/`: FastAPI service and supporting code
- `README.md`: Project overview and quickstart (this file)
- `backend/README.md`: Detailed backend docs (setup, env, APIs)

### Quickstart (backend)

1. Prerequisites

- Python 3.13
- Recommended: `uv` (`pip install uv`)

2. Configure environment

- Create `backend/.env.local` with at least the required API key (see `backend/README.md` for full details):

```
GOOGLE_API_KEY=your_google_api_key_here
```

3. Install & run (using uv)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Alternative (pip/venv):

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Explore the API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Useful links

- Detailed backend documentation: `backend/README.md`
- Issues/Roadmap: add as needed
