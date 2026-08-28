# ERP Natural-Language Business Q&A System

A deterministic, natural-language question-answering system over a small ERP dataset for an Indian mid-market manufacturer. 

This core application ensures that **the LLM never calculates numbers**. Factual answers are deterministically computed by querying structured PostgreSQL data based on a strongly-typed `QueryPlan`.

## Architecture
- **API**: FastAPI (`POST /ask`)
- **Database**: PostgreSQL (via Supabase) with SQLAlchemy and Alembic.
- **LLM Abstraction**: OpenAI Python client with OpenRouter and Instructor for structured outputs.
- **Strict Separation**: The LLM parses natural language into a typed QueryPlan. The plan is passed to a Metric Registry that executes verified Python/SQL logic. A Numeric Guard acts as a final fail-safe.

## Tech Stack
- Python 3.11+
- FastAPI, Pydantic, Uvicorn
- SQLAlchemy 2.0 (Async), asyncpg, Alembic
- OpenAI, Instructor

## Setup

1. **Clone the repository**
2. **Set up `.env`**:
   Copy `.env.example` to `.env` and fill in your actual credentials.
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/erp
   LLM_PROVIDER=openrouter
   LLM_MODEL=gpt-oss-120b
   LLM_API_KEY=your-api-key
   LOG_LEVEL=INFO
   ```
3. **Run via Docker Compose**:
   ```bash
   docker-compose up --build
   ```
4. **Local Development (without Docker)**:
   ```bash
   pip install -r requirements.txt # Or install via pip install -e .
   uvicorn app.main:app --reload
   ```

## Testing
Run tests locally with pytest:
```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Metric Definitions
See `docs/metric-definitions.md`.
## Safety Model
See `docs/architecture.md`.
# erp-chatbot
