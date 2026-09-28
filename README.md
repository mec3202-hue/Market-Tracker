# Analytics Job Market Tracker

Pulls analyst and data job postings every day, extracts the skills each one asks
for, and serves a web app showing which skills, salaries, and roles are trending.

**Stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · React (Vite) · Recharts ·
Docker · pytest · Vitest · GitHub Actions · Render

## What it does

- **Daily ingest.** Queries the [Adzuna API](https://developer.adzuna.com/) for US
  postings matching *data analyst*, *marketing analyst*, *business analyst*, and
  *analytics engineer*. Postings are deduplicated by Adzuna ID, so the job is safe to
  re-run.
- **Skill extraction.** Each title and description is matched against a catalog of
  about 50 skills (SQL, Python, dbt, Tableau, Power BI, Snowflake, …) using
  word-boundary regexes. Short names like `R`, `SAS`, and `SAP` are matched
  case-sensitively so that "R&D" or "remote" don't count.
- **Role classification.** Titles are sorted into buckets (Analytics Engineer, BI
  Analyst, Marketing Analyst, …). The search term that found a posting is used
  only as a fallback.
- **REST API** with validation and pagination (see below).
- **React frontend** with four views: trending skills (plus the biggest movers against
  the previous window), salary ranges by role or city, a skill gap checker, and a
  searchable list of postings.

## API

Interactive docs are served at `/docs` when the API is running.

| Endpoint | Description |
|---|---|
| `GET /skills/trending?days=30&limit=20&role=` | Share of postings mentioning each skill in the window, with the change from the previous window of the same length |
| `GET /salaries?role=&city=&group_by=role\|city&days=90&include_predicted=false&min_postings=3` | Average min/max and median midpoint salary per group |
| `GET /postings?skill=&role=&city=&q=&page=1&page_size=20` | Newest postings first, paginated (`total`, `pages`, `items`) |
| `POST /skills/gap` `{"skills": ["SQL","Excel"], "role": null, "top_n": 15}` | Your coverage of the top skills and which ones you're missing |
| `GET /skills` | Skill catalog |
| `GET /filters` | Roles and cities available for filtering, plus data freshness |
| `GET /health` | Liveness check |

Invalid input returns `422`. That includes out-of-range numbers, unknown roles or
skills, and an unknown `group_by`. Role, skill, and city filters are case-insensitive.
By default, salaries that Adzuna *estimated* rather than read from the posting are
left out.

## Running locally

### With Docker Compose

```bash
docker compose up --build
# Optional: load 600 synthetic postings so the charts have data without an API key
docker compose exec api python -m app.seed
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/docs

To pull real postings, get a free key at https://developer.adzuna.com/, then:

```bash
export ADZUNA_APP_ID=... ADZUNA_APP_KEY=...
docker compose up -d
docker compose exec api python -m app.ingest --pages 2
```

Seeded postings have IDs starting with `demo-`. Run `python -m app.seed --reset`
to replace them, or delete them before going live.

### Without Docker

```bash
# Backend (uses SQLite by default; set DATABASE_URL for Postgres)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit it
python -m app.seed
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Configuration

All settings come from environment variables (or `backend/.env`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./market_tracker.db` | `postgres://` and `postgresql://` URLs from Neon, Supabase, or Render work as-is |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | — | Required for `app.ingest` |
| `ADZUNA_COUNTRY` | `us` | |
| `SEARCH_TERMS` | the four roles above | Comma-separated |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of frontend origins |
| `VITE_API_URL` (frontend, build time) | `http://localhost:8000` | |

## Tests

```bash
cd backend && pytest                    # SQLite
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/tracker_test pytest   # Postgres

cd frontend && npm test && npm run lint
```

CI (`.github/workflows/ci.yml`) runs on every pull request. It runs ruff and pytest
against a Postgres 16 service, runs ESLint, Vitest, and the production build for the
frontend, and builds the API's Docker image.

## Deployment

1. **Database:** create a free Postgres database on [Neon](https://neon.tech) or
   [Supabase](https://supabase.com) and copy its connection string. Tables are
   created automatically on the API's first start.
2. **Render:** create a new Blueprint from this repo. `render.yaml` defines the API (a
   Docker web service) and the frontend (a static site). Set `DATABASE_URL` and
   `CORS_ORIGINS` on the API, and `VITE_API_URL` on the frontend.
3. **Daily ingest:** add the repository secrets `DATABASE_URL`, `ADZUNA_APP_ID`, and
   `ADZUNA_APP_KEY`. `.github/workflows/ingest.yml` runs every day at 11:17 UTC. You
   can also start it by hand from the Actions tab.

## Project layout

```
backend/
  app/
    main.py          FastAPI app and CORS
    config.py        environment-based settings
    models.py        postings and posting_skills tables
    skills.py        skill catalog, extraction, role classification
    ingest.py        Adzuna client and deduplicating loader (python -m app.ingest)
    seed.py          synthetic demo data (python -m app.seed)
    routers/         /skills, /salaries, /postings, /filters
  tests/
frontend/
  src/
    App.jsx          tabs and layout
    components/      TrendingSkills, Salaries, SkillGap, Postings
    api.js           API client
.github/workflows/   ci.yml, ingest.yml
docker-compose.yml
render.yaml
```

## Ideas for next steps

- Replace the regex matcher with a spaCy `PhraseMatcher` or NER model. The
  extractor is a single function, `extract_skills`, so it's easy to swap.
- Keep a daily snapshot table so trends can be charted over time.
- Add Alembic migrations once the schema starts changing.
