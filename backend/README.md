## Backend – CareerPilot API

FastAPI service that powers CareerPilot. Provides chat endpoints backed by Google Gemini via LangChain, with both standard and Server-Sent Events (SSE) streaming responses.

### Prerequisites

- Python 3.13
- Recommended: `uv` for dependency management (`pip install uv`)

### Environment configuration

Create `./.env.local` in the `backend/` directory:

```
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional (defaults shown)
MODEL_NAME=gemini-2.5-flash      # allowed: gemini-2.5-flash-lite | gemini-2.5-flash | gemini-2.5-pro
TEMPERATURE=0.0                  # 0.0 – 2.0
MAX_TOKENS=                      # empty for provider default
TIMEOUT=30
```

Notes:

- `GOOGLE_API_KEY` is validated at startup; empty/invalid values will raise an error.
- Config is loaded from `.env.local` via `pydantic-settings`.

### Install & Run

Using `uv` (recommended):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Using `pip` and venv:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

When running, the OpenAPI docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

- `GET /` – Welcome message
- `GET /health` – Health check
- `GET /chat?message=...` – Returns a JSON `ChatResponse`
- `GET /chat/stream?message=...` – Streams tokens via SSE (`meta`, `token`, `end`)

Example (non-streaming):

```bash
curl "http://localhost:8000/chat?message=Tell%20me%20a%20joke"
```

Example (streaming via SSE):

```bash
curl -N "http://localhost:8000/chat/stream?message=Tell%20me%20a%20joke"
```

Response model (`ChatResponse`):

```json
{
  "message": "string",
  "model": "string",
  "timestamp": "2024-01-01T12:00:00",
  "success": true
}
```

### Logging & Static Files

- Logs: written to `backend/logs/app.log` (created automatically if missing)
- Static files: served from `backend/static` at route `/static`

### Linting

`ruff` is configured in `pyproject.toml`.

```bash
uv run ruff check --fix .
```

### Troubleshooting

- Missing API key: ensure `GOOGLE_API_KEY` is set in `.env.local`.
- Model validation error: `MODEL_NAME` must be one of the allowed values listed above.
- Port already in use: change `--port` or stop the conflicting process.
- PowerShell execution policy: if activation fails, run PowerShell as admin and set policy appropriately.

### Project layout (backend)

- `src/app/main.py` – FastAPI app, CORS, static mounting, logging setup
- `src/app/api/v1/` – Routes: `index.py`, `chat.py`
- `src/app/services/chat_service.py` – LangChain chain and streaming
- `src/app/schemas/chat.py` – Pydantic models
- `src/app/core/config.py` – Settings and model definitions
