# CareerPilot - AI Coding Instructions

## Architecture Overview

CareerPilot is a monorepo with a **FastAPI backend** and **Next.js 15 frontend** for AI-powered resume analysis and career guidance.

### Core Data Flow
1. User uploads resume PDF → `POST /resume/upload` → `ResumeProcessor` converts to structured JSON
2. JSON stored in PostgreSQL (pgvector) → `ResumeProfile` model with `raw_data` JSON field
3. Analysis endpoints query resume via `user_id` → LangChain tools fetch data → AI generates insights
4. Frontend hooks (`useAnalysis.ts`, `useJobs.ts`) consume REST API via `@tanstack/react-query`
5. On upload success, frontend prefetches overview/jobs/career-path for smoother UX

### Key Service Boundaries
- **Resume Processing**: `backend/src/app/services/resume_processing/` - PDF→markdown→structured JSON
- **Agent Service**: `backend/src/app/services/agent/agent.py` - LangChain tool-calling agent with `ConversationMemory`
- **Analysis Service**: `backend/src/app/services/analysis_service.py` - Resume scoring, skills gap, career paths (uses `asyncio.gather` for parallel tool calls)
- **ATS Service**: `backend/src/app/services/ats_service.py` - LLM-powered semantic ATS scoring
- **Frontend API Layer**: `frontend/src/lib/api.ts` - Centralized `apiRequest()` with timeout handling

## Development Commands

### Backend (Python 3.13 + uv)
```bash
cd backend
uv sync                                    # Install dependencies
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
uv run ruff check --fix .                  # Lint and auto-fix
```

### Frontend (Node.js + npm)
```bash
cd frontend
npm install
npm run dev                                # Turbopack dev server on :3000
```

### Docker (full stack with PostgreSQL + pgvector)
```bash
cd backend
docker compose up -d                       # Starts db, api, runs init_db
```

## Environment Configuration

Backend requires `.env.local` in `backend/`:
```
GOOGLE_API_KEY=...                         # Required - Gemini API
TAVILY_API_KEY=...                         # Required - web search for jobs
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/careerpilot
MODEL_NAME=gemini-2.5-flash                # Options: gemini-2.5-flash-lite | gemini-2.5-flash | gemini-2.5-pro
```

Frontend uses `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

## Code Patterns

### Backend API Routes
Routes live in `backend/src/app/api/v1/`. Each route file follows:
```python
router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/overview")
async def get_analysis_overview(user_id: str = Query(...)) -> dict[str, Any]:
    result = await analysis_service.get_overview(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
```

### Parallel Async Operations
Use `asyncio.gather` for concurrent operations:
```python
strengths, improvements, metrics = await asyncio.gather(
    analyze_resume_strengths_tool(user_id),
    suggest_improvements_tool(user_id),
    get_resume_metrics_tool(user_id),
)
```

### Agent Tool Definition
Tools in `backend/src/app/services/agent/tools/` are decorated with `@tool` and registered in `AgentService._build_tools()`:
```python
@tool("get_skills", return_direct=False)
async def agent_get_skills(user_id: str) -> dict[str, Any]:
    """Docstring becomes tool description for LLM."""
    return await get_skills_tool(user_id=user_id)
```

### Frontend Data Fetching with Caching
Use React Query hooks from `frontend/src/hooks/queries/` with staleTime/gcTime for performance.
Data is persisted to localStorage via `frontend/src/lib/query-persister.ts` for offline access:
```typescript
import { getCachedData, setCachedData } from "@/lib/query-persister";

const STALE_TIME = 10 * 60 * 1000; // 10 minutes
const CACHE_TIME = 60 * 60 * 1000; // 60 minutes

export function useJobRecommendations(userId: string | null, limit = 10) {
  const queryKey = ["jobs", "recommendations", userId, limit];
  const cachedData = getCachedData<JobRecommendations>(queryKey);
  
  const query = useQuery({
    queryKey,
    queryFn: () => apiRequest<JobRecommendations>(`/jobs/recommendations?user_id=${userId}&limit=${limit}`),
    enabled: !!userId,
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    initialData: cachedData,
    initialDataUpdatedAt: cachedData ? Date.now() - 60000 : undefined,
  });
  
  useEffect(() => {
    if (query.isSuccess && query.data) {
      setCachedData(queryKey, query.data);
    }
  }, [query.isSuccess, query.data]);
  
  return query;
}
```

### Prefetching on Upload
After resume upload, clear old cache and prefetch key data for smoother navigation:
```typescript
import { clearCache, setCachedData } from "@/lib/query-persister";

const prefetchRecommendations = async (userId: string) => {
  clearCache(); // Clear old resume data
  
  const fetchAndPersist = async <T,>(queryKey: unknown[], endpoint: string) => {
    const data = await apiRequest<T>(endpoint);
    queryClient.setQueryData(queryKey, data);
    setCachedData(queryKey, data);
    return data;
  };

  await Promise.allSettled([
    fetchAndPersist(["analysis", "overview", userId], `/analysis/overview?user_id=${userId}`),
    fetchAndPersist(["jobs", "recommendations", userId, 10], `/jobs/recommendations?user_id=${userId}&limit=10`),
    fetchAndPersist(["analysis", "career-path", userId], `/analysis/career-path?user_id=${userId}`),
  ]);
};
```

### Database Session Pattern
Use context manager for transactions:
```python
from app.infrastructure.database.connection import get_session

with get_session() as session:
    repo = ResumeRepository(session)
    profile = repo.get_by_id(profile_id)
```

## Key Files Reference

| Purpose | Location |
|---------|----------|
| FastAPI app entry | `backend/src/app/main.py` |
| Settings/config | `backend/src/app/core/config.py` |
| Database models | `backend/src/app/infrastructure/database/models.py` |
| Resume processor | `backend/src/app/services/resume_processing/processors/processor.py` |
| Agent with tools | `backend/src/app/services/agent/agent.py` |
| ATS service (LLM) | `backend/src/app/services/ats_service.py` |
| Chat history API | `backend/src/app/api/v1/chat.py` |
| Analysis types | `frontend/src/types/analysis.ts` |
| API client | `frontend/src/lib/api.ts` |
| React Query hooks | `frontend/src/hooks/queries/` |
| LocalStorage cache | `frontend/src/lib/query-persister.ts` |
| Markdown renderer | `frontend/src/components/ui/markdown-renderer.tsx` |
| UI components | `frontend/src/components/analysis/` |

## Conventions

- **Pydantic for validation**: All settings use `pydantic-settings`, API models use Pydantic
- **Ruff for linting**: Configured in `pyproject.toml` with Black-compatible formatting
- **Singleton services**: Services like `chat_service`, `analysis_service`, `ats_service` are instantiated as module-level singletons
- **User ID flow**: Resume upload returns `user_id` → all subsequent API calls require `user_id` query param
- **SSE streaming**: Chat endpoint supports streaming via `/chat/stream` with `sse-starlette`
- **Role definitions**: Skills gap analysis supports roles: Backend, Frontend, Full-Stack, ML Engineer, Data Scientist, AI Engineer, Data Engineer, DevOps, Cloud, Mobile (see `_get_role_requirements`)
- **Chat history**: Stored in `conversations` and `messages` tables, accessible via `/chat/history` endpoints
