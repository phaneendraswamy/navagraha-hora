# AI Resume Intelligence System

Production-ready scaffold for generating JD-tailored, ATS-friendly resumes with Streamlit, FastAPI, PostgreSQL, OpenAI, Sentence Transformers, PDF export, and DOCX export.

## Features

- Raw profile ingestion from pasted text, PDF, DOCX, or TXT so the app can build a candidate knowledge base before resume generation
- Structured master profile storage with SQLAlchemy ORM and PostgreSQL
- JD upload or paste flow for PDF, DOCX, and TXT
- Regex + optional OpenAI JD analysis
- Role classification for Data Analyst, Data Engineer, AI Engineer, ML Engineer, NLP Engineer, and BI Developer
- Sentence Transformers semantic matching for projects and experience
- ATS keyword match score, missing keywords, suggestions, and ranked projects
- OpenAI-powered summary and bullet rewriting with anti-hallucination prompts
- DOCX and PDF export with clean bordered ATS-friendly formatting
- Streamlit workspace with Profile Knowledge, JD Match, and Resume Studio tabs

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On Windows PowerShell, you can also run:

```powershell
.\scripts\setup_windows.ps1
```

Create PostgreSQL database:

```sql
CREATE DATABASE resume_ai;
```

Or start the included local PostgreSQL container:

```bash
docker compose up -d postgres
```

Update `.env` with your PostgreSQL URL and `OPENAI_API_KEY`.

## Run

Start the API:

```bash
python -m uvicorn backend.main:app --reload
```

In a second terminal, seed the sample profile:

```bash
python scripts/seed_profile.py data/master_profile.json
```

In a third terminal, start the Streamlit UI:

```bash
python -m streamlit run frontend/app.py
```

Open `http://localhost:8501`.

## Windows / PowerShell Notes

Run long-lived services in separate terminals. `uvicorn` stays running, so commands after it will not execute until the server stops.

If `docker compose up -d postgres` fails with a Docker pipe error, start Docker Desktop first, then retry. If you do not use Docker, install PostgreSQL locally, create the `resume_ai` database, and update `DATABASE_URL` in `.env`.

If `uvicorn` or `streamlit` is not recognized, use the module form shown above: `python -m uvicorn ...` and `python -m streamlit ...`.

### No-Docker Local Dev Option

For quick local testing without Docker or PostgreSQL, use SQLite:

```powershell
copy .env.sqlite.example .env
python -m uvicorn backend.main:app --reload
```

Then seed and run the UI from separate terminals:

```powershell
python scripts/seed_profile.py data/master_profile.json
python -m streamlit run frontend/app.py
```

Use PostgreSQL again for production-like testing by restoring `DATABASE_URL` from `.env.example`.

## API Routes

- `GET /health`
- `POST /profile`
- `POST /jd/analyze`
- `POST /jd/upload`
- `POST /resume/generate`
- `GET /exports/{filename}`

The explicit SQL schema is available at `docs/schema.sql`; the app also creates tables automatically through SQLAlchemy on API startup.

## Security Notes

- API keys are read from `.env`; do not commit real secrets.
- Uploads are extension and size validated.
- JD text is sanitized for control characters and common prompt-injection phrases.
- Resume rewriting prompts explicitly forbid inventing unsupported experience.

## OpenAI Integration

The backend uses the OpenAI Python SDK and the Responses API. If no API key is configured, the app falls back to deterministic regex parsing and non-AI resume text so local development still works.

## Extending

- Add real DOCX template binding in `backend/resume_generator.py`
- Add authentication and multi-user tenancy before SaaS deployment
- Add vector persistence for faster repeated matching
- Add cover letter, LinkedIn summary, and portfolio generation routes
