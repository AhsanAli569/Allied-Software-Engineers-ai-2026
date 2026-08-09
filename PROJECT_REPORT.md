# ASE AI — Project Report

**Product**: Allied Software Engineers Artificial Intelligence (ASE AI)
**Repo**: https://github.com/AhsanAli569/Allied-Software-Engineers-ai-2026

A conversational AI web app: accounts, persistent chats, streaming responses, image/document
attachments, and a pluggable AI provider layer with automatic fallback.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 (**JavaScript**, no TypeScript) + Vite, Tailwind CSS, React Router |
| Backend | Python 3.12 + **FastAPI**, async throughout |
| ORM / Migrations | SQLAlchemy 2 (async) + Alembic |
| Database | **PostgreSQL** (production) — SQLite supported as a local-dev fallback |
| Auth | Argon2id password hashing, JWT access token + rotating refresh token, both in httpOnly cookies, CSRF double-submit protection |
| AI Providers | Google Gemini, Groq, OpenRouter — behind one interface (`AIProvider`) with automatic priority-ordered fallback |
| File storage | Local disk (dev/VPS); attachments validated by real file signature, not filename |
| Streaming | Server-Sent Events (SSE) |
| Testing | pytest — 46 backend tests (auth, IDOR/ownership, provider fallback, attachments) |
| Deployment | Docker Compose + nginx (VPS path) **or** Netlify (frontend) + Render (backend) + Neon (Postgres) — free-tier path |

## Features Implemented

- Registration/login, password change, logout / logout-all-devices
- Unlimited conversations: create, rename, pin, archive, soft-delete, search
- Streaming chat with stop/regenerate/copy
- Image upload → vision-capable model; document upload (PDF/DOCX/TXT/MD/CSV) → text extracted and used as context
- Automatic AI provider fallback (Gemini → Groq → OpenRouter), model/provider never exposed in the UI
- Light/dark/system theme, Allied Software Engineers brand palette, fully responsive (mobile drawer sidebar)
- Security: parameterized queries only, per-request ownership checks (no IDOR), CSRF, rate limiting, real file-signature validation on uploads, no secrets in the frontend bundle

## Not Yet Built (explicitly deferred)

Vector-search/RAG across documents with citations, admin dashboard, self-hosted model support, public developer API, email/SMTP, Redis (in-memory rate limiter stands in for now).

## Status

Backend: 46/46 tests passing. Frontend: builds and lints clean. Both verified live end-to-end
(register → chat → streamed AI response → attachments) against real provider APIs.
