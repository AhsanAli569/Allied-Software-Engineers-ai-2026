# ASE AI — Installation (Local Development, Windows)

## Prerequisites

- **Python 3.11 or 3.12** — not 3.14+. Several backend dependencies (e.g. `argon2-cffi`,
  `asyncpg`, `pydantic`) don't yet ship prebuilt wheels for very new Python releases, which
  forces `pip` into a source build that needs a Rust toolchain and usually fails. If you have
  multiple Python versions installed, use the launcher to pick one:
  `py -0p` lists installed versions; create the venv with e.g.
  `py -3.12 -m venv .venv`.
- **Node.js 18+** and npm.
- **PostgreSQL 16** (native Windows installer — recommended over Docker if Docker doesn't run
  on your machine due to virtualization/Hyper-V conflicts, which is common). Download from
  postgresql.org and remember the password you set for the `postgres` superuser.
- Redis is **not** required for Phase 1 — rate limiting uses an in-memory store for local dev.

## 1. Database

After installing PostgreSQL, create a database and a dedicated user (using `psql` or pgAdmin):

```sql
CREATE USER ase_ai WITH PASSWORD 'changeme';
CREATE DATABASE ase_ai OWNER ase_ai;
```

## 2. Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`:
- Set `DATABASE_URL` to match the database you created, e.g.
  `postgresql+asyncpg://ase_ai:changeme@localhost:5432/ase_ai`
- Generate a real `JWT_SECRET`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- Add your AI provider keys (see below) — never commit `.env` or paste keys anywhere public.

Run migrations (creates all tables and seeds the model registry):

```bash
alembic upgrade head
```

Create the first administrator account:

```bash
python -m app.cli create-admin
```

Start the API:

```bash
uvicorn app.main:app --reload
```

It listens on `http://localhost:8000` by default. **If you see `WinError 10013` (access
forbidden) binding to port 8000**, Hyper-V/WSL has likely reserved that port in its dynamic
exclusion range (common on machines with Docker Desktop or WSL installed, even if Docker
itself doesn't run). Run on a different port instead — `uvicorn app.main:app --reload --port
8010` — and update `frontend/vite.config.js`'s proxy `target` to match.

Check it's alive: `curl http://localhost:8000/api/v1/health`

### AI provider keys

Add whichever you have to `backend/.env` — the app works with any subset configured (models
from providers without a key simply won't be tried):

- **Gemini**: create a key at Google AI Studio (`GEMINI_API_KEY`).
- **Groq**: create a key at console.groq.com (`GROQ_API_KEY`).
- **OpenRouter**: create a key at openrouter.ai (`OPENROUTER_API_KEY`).

With no keys configured at all, chat requests will fail gracefully with "No AI provider is
currently available" rather than crashing — useful for testing everything else first.

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The dev server proxies `/api/*` to the backend (see
`vite.config.js`), so the browser only ever talks to one origin and cookie-based auth works
without cross-site cookie complications.

## 4. Running tests

```bash
cd backend
pytest
```

Tests run against an isolated in-memory SQLite database (no Postgres required) — see
`backend/tests/conftest.py`. This is why the ORM models use a cross-dialect `GUID` type
instead of PostgreSQL's native `UUID`.

## 5. Production build (frontend)

```bash
cd frontend
npm run build   # outputs to frontend/dist
npm run preview # serve the production build locally to sanity-check it
```
