# Analytics Job Market Tracker

Pulls analyst and data job postings every day, extracts the skills each one asks
for, and serves a web app showing which skills, salaries, and roles are trending.

**Stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · React (Vite) · Recharts ·
Docker · pytest · Vitest · GitHub Actions · Render

## What it does

- **Daily ingest.** Queries the [Adzuna API](https://developer.adzuna.com/) for US
  postings across 10 search terms (data, marketing, business, BI, product, financial,
  operations, and reporting analyst, plus analytics engineer and data scientist).
  Postings are deduplicated by Adzuna ID, so the job is safe to re-run. Requests are
  paced to stay within Adzuna's free limits (25 a minute, 250 a day).
- **Skill extraction.** Each title and description is matched against a catalog of
  about 50 skills (SQL, Python, dbt, Tableau, Power BI, Snowflake, …) using
  word-boundary regexes. Short names like `R`, `SAS`, and `SAP` are matched
  case-sensitively so that "R&D" or "remote" don't count.
- **Role classification.** Titles are sorted into buckets (Analytics Engineer, BI
  Analyst, Marketing Analyst, …). The search term that found a posting is used
  only as a fallback.
- **Location and work setting.** Each posting's state and city come from Adzuna.
  Whether it's **remote**, **hybrid**, or **on-site / not stated** is detected from its
  text. Negations like "not a remote role" and phrases like "remote sensing" or
  "hybrid cloud" are handled.
- **REST API** with validation and pagination (see below).
- **React frontend** with a shared filter bar (role, state, city, work setting) that
  applies to every view:
  - trending skills, plus the biggest movers against the previous window
  - salary ranges by role, state, city, or work setting
  - locations & remote: the remote / hybrid / on-site split, and postings by state
    (click a state to see its cities)
  - a skill gap checker
  - a searchable list of postings

## API

Interactive docs are served at `/docs` when the API is running.

Every data endpoint accepts the same **scope** filters: `role`, `state` (a name or a
two-letter code, such as `CA`), `city`, and `work_mode` (`remote`, `hybrid`, or `onsite`).

| Endpoint | Description |
|---|---|
| `GET /skills/trending?days=30&limit=20` | Share of postings mentioning each skill in the window, with the change from the previous window of the same length |
| `GET /salaries?group_by=role\|state\|city\|work_mode&days=90&include_predicted=false&min_postings=3` | Average min/max and median midpoint salary per group |
| `GET /locations?days=90&limit=25` | Remote / hybrid / on-site split, plus postings, remote share, and median salary by state (or by city when `state` is set) |
| `GET /postings?skill=&q=&page=1&page_size=20` | Newest postings first, paginated (`total`, `pages`, `items`) |
| `POST /skills/gap` `{"skills": ["SQL","Excel"], "state": "TX", "work_mode": "remote", "top_n": 20}` | Your coverage of the top skills and which ones you're missing |
| `GET /skills` | Skill catalog |
| `GET /filters` | Roles, states, and cities available for filtering, plus data freshness |
| `GET /health` | Liveness check |

Invalid input returns `422`. That includes out-of-range numbers, unknown roles,
skills, or work settings, and an unknown `group_by`. Role, skill, and city filters are case-insensitive.
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
| `SEARCH_TERMS` | the 10 roles above | Comma-separated |
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

### Option A: GitHub Pages (everything on GitHub, no server)

The site is published at `https://<your-user>.github.io/<repo>/`. GitHub Pages
serves only static files, so `.github/workflows/pages.yml` exports the data to JSON
(`python -m app.export_static`), and the React app computes every view from those
files in the browser (`VITE_STATIC_DATA=1`). The results match the API's.

The export holds every posting from the last 180 days in a compact form of about
50 bytes each, for the charts. It also includes the 3,000 newest postings in full,
for the postings list.

1. Create a free Postgres database on [Neon](https://neon.tech) and add these
   repository secrets under Settings → Secrets and variables → Actions:
   `DATABASE_URL`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY`.
2. Under Settings → Pages → Build and deployment, set **Source** to **GitHub Actions**.
3. Under Actions → **Daily ingest**, click **Run workflow**. For the first run, set
   *max_days_old* to `30` to backfill a month of postings. When it finishes,
   **Deploy to GitHub Pages** runs automatically and publishes the site. After
   that, it updates every day.
4. *(Optional)* To use a custom domain, enter it under Settings → Pages →
   Custom domain and add the DNS record GitHub shows you. The next deploy
   picks up the new address automatically.

### Option B: Render (live API)

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
    export_static.py JSON export for the GitHub Pages build
    seed.py          synthetic demo data (python -m app.seed)
    routers/         /skills, /salaries, /postings, /filters
  tests/
frontend/
  src/
    App.jsx          tabs and layout
    components/      TrendingSkills, Salaries, SkillGap, Postings
    api.js           API client (HTTP, or static mode)
    staticApi.js     the API computed in the browser from exported JSON
.github/workflows/   ci.yml, ingest.yml, pages.yml
docker-compose.yml
render.yaml
```

## Ideas for next steps

- Replace the regex matcher with a spaCy `PhraseMatcher` or NER model. The
  extractor is a single function, `extract_skills`, so it's easy to swap.
- Keep a daily snapshot table so trends can be charted over time.
- Replace the small built-in migration in `db.py` with Alembic if the schema keeps
  changing.
