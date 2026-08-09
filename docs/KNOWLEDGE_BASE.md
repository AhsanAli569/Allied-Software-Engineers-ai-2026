# Business knowledge base (RAG)

ASE AI can ground its answers in Allied Software Engineers' own business information
(services, pricing, policies, team, portfolio, etc.) instead of guessing or saying it
doesn't know. This works via retrieval-augmented generation (RAG):

1. You provide business documents (`.txt`, `.md`, `.pdf`, `.docx`).
2. `python -m app.cli ingest-knowledge <path>` splits each document into chunks, embeds
   them with Gemini's embedding model, and stores them in the `knowledge_chunks` table.
3. On every chat message, the backend embeds the user's question, finds the most similar
   stored chunks (if any score high enough), and quietly adds them as extra context before
   asking the AI to answer — the user never sees this happen, same as model routing.

If nothing relevant is found (empty knowledge base, or no chunk is a close match), the
request proceeds exactly as before — this never blocks or slows down a response beyond one
extra embedding call, and fails open (skips silently) if that call errors.

## Adding your content

1. Put your business documents in a folder, e.g. `backend/knowledge/`:
   - `about.txt`, `services.md`, `pricing.pdf`, `policies.docx` — any mix of the four
     supported types.
2. From `backend/`, with your virtualenv active and `GEMINI_API_KEY` set in `.env`:
   ```
   python -m app.cli ingest-knowledge ./knowledge
   ```
   (or point it at a single file: `python -m app.cli ingest-knowledge ./knowledge/pricing.pdf`)
3. It prints how many chunks were stored per file. Re-run any time a document changes —
   re-ingesting a file replaces its previous chunks (matched by filename), it doesn't
   duplicate them.

To update the **production** knowledge base (Render + Neon), run the same command from a
machine whose `DATABASE_URL` and `GEMINI_API_KEY` point at your production Neon database and
Gemini key — either locally with `backend/.env` temporarily pointed at the Neon connection
string, or via Render's shell if your plan includes one. This is a deliberate one-off CLI
step, not an admin UI, matching how `create-admin` already works.

## Notes

- Embeddings always go through Gemini (`text-embedding-004`), regardless of which provider
  ends up answering the chat message — this is independent of the automatic model-fallback
  routing used for chat itself.
- Retrieval is a plain cosine-similarity search over stored embeddings in Python (no vector
  database extension required) — fine at the scale of a hand-curated business knowledge
  base. If the corpus grows into the tens of thousands of chunks, revisit with pgvector.
- `backend/knowledge/` is a suggested convention, not a special path — `ingest-knowledge`
  accepts any file or directory. Consider adding it to `.gitignore` if the documents
  themselves shouldn't be committed to the repo.
