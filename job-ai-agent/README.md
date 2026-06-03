# AI Job Hunter

Production-minded MVP for AI-powered job aggregation, normalization, scoring, JD intelligence, and human-approved application tracking.

## MVP Scope

Implemented now:

- FastAPI backend
- PostgreSQL SQLAlchemy models
- Raw job storage before normalization
- Greenhouse API collector
- Conservative LinkedIn Playwright collector
- Weighted matching engine
- JD intelligence extraction
- Streamlit review dashboard
- Human approval workflow with Apply, Save, Skip, and View Full JD
- Docker Compose setup
- Alembic migration scaffold

Auto-apply is intentionally not implemented in this MVP.

## Architecture

```text
collectors -> raw_jobs -> parsers/normalizer -> jobs -> ai_engine/matcher -> dashboard decisions
```

Key directories:

- `backend/`: FastAPI app, API routes, database models, ingestion service
- `collectors/`: LinkedIn and Greenhouse collection
- `parsers/`: source-specific normalization into the standard schema
- `ai_engine/`: match scoring and JD intelligence
- `frontend/`: Streamlit dashboard
- `database/`: init SQL and Alembic migrations
- `workflows/`: collection orchestration and scheduler placeholder
- `resume_optimizer/`: conservative resume suggestion placeholder
- `tests/`: focused unit tests

## Matching Logic

Initial weighted scoring:

- Skill overlap: 50%
- Experience relevance: 25%
- Location relevance: 15%
- Tooling overlap: 10%

The result includes component scores, strong matches, missing skills, reasoning, and confidence.

## Setup

Copy environment variables:

```bash
cp .env.example .env
```

Run with Docker:

```bash
docker compose up --build
```

Open:

- API: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`

## Local Development

Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Start PostgreSQL locally or through Docker:

```bash
docker compose up postgres
```

Run the API:

```bash
uvicorn backend.main:app --reload
```

Run Streamlit:

```bash
streamlit run frontend/app.py
```

Run tests:

```bash
pytest
```

## Collector Notes

Greenhouse uses the official public board API.

LinkedIn uses small Playwright batches, human-like delays, no credential automation, and no bypass logic. It may return limited results if LinkedIn blocks public pages or changes markup.

## Example API Calls

Collect Greenhouse jobs:

```bash
curl -X POST http://localhost:8000/api/collect/greenhouse ^
  -H "Content-Type: application/json" ^
  -d "{\"boards\":[\"openai\",\"stripe\"]}"
```

List ranked jobs:

```bash
curl "http://localhost:8000/api/jobs?limit=25&min_match=60"
```

Approve a job:

```bash
curl -X PATCH http://localhost:8000/api/jobs/{job_id}/decision ^
  -H "Content-Type: application/json" ^
  -d "{\"decision_status\":\"approved\"}"
```

## Next Steps

1. Add richer JD parsing with spaCy.
2. Add ChromaDB embeddings for semantic role matching.
3. Add resume upload and truthful resume tailoring.
4. Add application form assistance only after approval.
5. Add scheduled collection with per-source rate limits and audit logs.

