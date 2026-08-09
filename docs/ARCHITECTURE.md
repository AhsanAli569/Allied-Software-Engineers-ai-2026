# ASE AI — Architecture (Phase 1)

## Overview

```
Browser (React SPA)
   │  cookies (httpOnly access/refresh JWT + non-httpOnly CSRF token)
   ▼
FastAPI backend  ──►  PostgreSQL (users, conversations, messages, ai_models, sessions, audit_logs)
   │
   ▼
ProviderRouter (priority + fallback + capped exponential backoff)
   │
   ├─► GeminiProvider     (Google Generative Language API)
   ├─► GroqProvider       (OpenAI-compatible)
   └─► OpenRouterProvider (OpenAI-compatible)
```

The frontend never talks to Gemini/Groq/OpenRouter directly and never sees their API keys —
every AI call is proxied through the backend's `ProviderRouter`.

## Provider abstraction

`app/providers/base.py` defines `AIProvider`, an abstract interface every backend implements:
`chat`, `stream_chat`, `vision`, `analyze_document`, `embeddings`, `transcribe`,
`health_check`, `list_models`. Phase 1 implements `chat`/`stream_chat` for Gemini, Groq, and
OpenRouter; the multimodal/document/embedding/transcription methods raise `NotImplementedError`
until later phases wire them up — the interface is already shaped for that so adding a provider
or a capability doesn't require touching call sites elsewhere in the app.

Which model/provider gets tried is driven entirely by the `ai_models` **database table** (the
"model registry" from the spec), not hard-coded — an admin can reprioritize or disable a model
without a redeploy. `ProviderRouter.stream_chat_with_fallback` walks the active models in
priority order; on a rate-limit/timeout/5xx/auth error *before any content has been sent to the
client*, it moves to the next candidate with capped exponential backoff (never an unbounded
retry loop). Once a provider has started streaming content to the client, a further failure is
**not** silently papered over by switching providers mid-response — that would splice output
from two different models into one answer. Instead the partial response is marked `failed` and
the client sees a friendly error.

## Streaming

Server-Sent Events, not WebSockets — one-directional token streaming doesn't need a
bidirectional channel, and SSE needs no extra infrastructure (no Redis pub/sub) for a
single-process dev/small-prod deployment. The frontend can't use the browser's built-in
`EventSource` because it only supports GET; `frontend/src/lib/sse.js` parses the
`text/event-stream` body off a normal `fetch()` instead, which also gives us an
`AbortController`-based cancel path for the "stop generation" button.

The assistant `messages` row is created (status `streaming`) only once a provider has
committed to responding — so a totally failed generation (all providers down) leaves no
empty assistant row in history. Cancelling mid-stream persists whatever content had already
arrived with status `cancelled`, so nothing is lost.

## Context management

`app/services/message_service.py::build_context_messages` sends only the last 20
user/assistant messages (plus the system prompt) to the provider on each turn — not the
entire conversation history — bounding token usage as conversations grow. This is a fixed
recent-window strategy for Phase 1; semantic retrieval/summarization for very long
conversations is a later-phase enhancement.

## Auth

- Argon2id password hashing.
- Short-lived (15 min) JWT access token in an httpOnly cookie.
- Opaque refresh token, SHA-256-hashed at rest in the `sessions` table, rotated on every
  `/auth/refresh` call (old token is immediately invalidated — single-use), individually
  revocable (`/auth/logout`) or all-at-once (`/auth/logout-all`, also triggered by a password
  change).
- CSRF: double-submit cookie. A non-httpOnly `ase_csrf_token` cookie is set alongside the auth
  cookies; state-changing requests must echo it back in an `X-CSRF-Token` header. A cross-site
  page can trigger the cookie to be sent automatically but can't read it to set the header.

## Data isolation (IDOR prevention)

Every conversation/message lookup goes through
`app/services/conversation_service.py::get_owned_conversation`, which filters by
`conversation_id AND user_id` together — never `conversation_id` alone. A request for another
user's conversation gets a 404 (not a 403), so the existence of other users' data is never
leaked. This is explicitly covered by `backend/tests/test_conversation_ownership.py`.

## What's deliberately out of Phase 1

File/image uploads, PDF/RAG, vector DB, admin dashboard, Redis (an in-memory rate limiter
stands in for now — documented as dev-only in `app/middleware/rate_limit.py`), Docker Compose,
CI/CD, the public ASE API, self-hosted vLLM, email/SMTP, and message-edit branching UI. The
schema already has the hooks for some of these (`messages.parent_message_id`,
`users.role` for RBAC) so they can be built on top without a schema rewrite.
