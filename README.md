# ASE AI — Allied Software Engineers Artificial Intelligence

**Intelligence Engineered for Everyone**

ASE AI is Allied Software Engineers' conversational AI platform: secure accounts, persistent
conversations, streaming responses, and a pluggable AI provider layer (Gemini → Groq →
OpenRouter, with automatic fallback) that can later be extended with self-hosted models.

This repository currently implements **Phase 1**: authentication, streaming chat, conversation
management, and the provider abstraction. File uploads/RAG, the admin panel, self-hosted model
support, and the public API are planned for later phases (see `docs/ARCHITECTURE.md`).

## Stack

- **Backend**: FastAPI, SQLAlchemy 2 (async), PostgreSQL, Alembic, Argon2id + JWT auth
- **Frontend**: React 18 (JavaScript, Vite) — a plain SPA, no Next.js/TypeScript
- **AI providers**: Google Gemini, Groq, OpenRouter (free tiers), behind a common interface

## Quick start

See `docs/INSTALLATION.md` for full setup. Short version:

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # fill in DATABASE_URL and provider API keys
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design, provider fallback, data model
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — local setup, migrations, running tests

## Testing

```bash
cd backend
pytest
```

---

© Allied Software Engineers. All Rights Reserved.
