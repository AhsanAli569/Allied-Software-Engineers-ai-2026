# ASE AI — Deploying on Netlify (frontend) + Render (backend) + Neon (database)

A fully free alternative to the single-VPS setup in `docs/DEPLOYMENT.md`. Different topology
though — frontend and backend live on **different domains**, so this doesn't use
`docker-compose.prod.yml` or the nginx config at all. Read the limitations below before
you commit to this path.

## Known limitations (accepted trade-offs of the free tiers)

- **Uploaded files are not durable.** Render's free web services have no persistent disk —
  attachments (images/documents) can be deleted whenever the service restarts, redeploys,
  or wakes from sleep. Fine for testing/demo use; don't rely on uploaded files staying
  around long-term. (Swapping in S3-compatible storage like Cloudflare R2 later would fix
  this without much rework — ask if you want that added.)
- **Cold starts.** Render free web services sleep after 15 minutes of inactivity. The first
  request after idle takes ~30-50s to wake up; the chat may look "stuck" briefly on that
  first message.
- **Cross-site cookies.** Because the frontend and backend are on different domains, auth
  cookies use `SameSite=None`. This is standards-compliant and works in all modern
  browsers, but is a fundamentally less contained setup than a single-domain deployment —
  some privacy-hardened browser configurations (aggressive third-party cookie blocking)
  could interfere. If you hit login issues that don't reproduce on the VPS setup, this is
  the first thing to suspect.

## 1. Database — Neon

1. Sign up at neon.tech, create a project (any region close to your Render region).
2. Copy the connection string from the dashboard. It looks like:
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`
3. Adapt it for our async driver — change the scheme and the SSL param name:
   `postgresql+asyncpg://user:password@ep-xxx.region.aws.neon.tech/dbname?ssl=require`
   (asyncpg wants `ssl=`, not libpq's `sslmode=`.)
   Keep this — it's your `DATABASE_URL`.

## 2. Backend — Render

**Option A: Blueprint (faster).** In the Render dashboard: New → Blueprint → point it at
this repo (`render.yaml` is at the repo root). Render provisions the service; you'll still
need to fill in the `sync: false` values (`DATABASE_URL`, `CORS_ORIGINS`, provider keys) in
the service's Environment tab afterward.

**Option B: Manual (if the blueprint fails to parse, or you'd rather see each setting):**

1. New → Web Service → connect this repo.
2. **Root Directory**: `backend`
3. **Runtime**: Docker (Render will detect `backend/Dockerfile`)
4. **Instance Type**: Free
5. **Health Check Path**: `/api/v1/health`
6. **Environment variables** — add everything from `backend/.env.example`, with these
   values specifically for this deployment:
   - `DATABASE_URL` = the Neon string from step 1
   - `ENVIRONMENT=production`, `DEBUG=false`
   - `JWT_SECRET` = generate one: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
   - `COOKIE_SAMESITE` — leave unset. `ENVIRONMENT=production` alone now makes the backend
     default cookies to `SameSite=None` automatically (needed since Netlify and Render are
     different domains); only set this explicitly if you want to override that default.
   - `CORS_ORIGINS` = your Netlify URL (you'll know this after step 3 below; come back
     and set it, then redeploy)
   - `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` = whichever you have
7. Deploy. Migrations run automatically on startup (`entrypoint.sh`).
8. Note the service URL Render gives you, e.g. `https://ase-ai-backend.onrender.com` —
   you'll need `https://ase-ai-backend.onrender.com/api/v1` for the frontend.

### Create your admin account

Render dashboard → your service → **Shell** tab:
```bash
python -m app.cli create-admin
```

## 3. Frontend — Netlify

1. Add site → Import an existing project → connect this repo.
2. **Base directory**: `frontend` (Netlify will pick up `frontend/netlify.toml` from here,
   which already sets the build command, publish directory, and the SPA redirect rule)
3. **Environment variable**: `VITE_API_URL` = `https://ase-ai-backend.onrender.com` (your
   actual Render URL — with or without a trailing `/api/v1`, `src/lib/api.js` normalizes
   either form, so don't worry about getting that part exactly right)
4. Deploy. Note the Netlify URL, e.g. `https://your-app.netlify.app`.

   **Double-check the variable name is exactly `VITE_API_URL`.** Vite only exposes
   `VITE_*`-prefixed env vars to the frontend, and it does so by exact name — a typo or a
   different name (this has happened: `VITE_API_BASE_URL` was used in an earlier version of
   this doc) means the app silently falls back to relative `/api/v1` paths, which Netlify's
   own SPA routing then answers with `index.html` instead of JSON. `netlify.toml` now
   returns a real 404 for that case instead of masking it, so if this regresses again the
   symptom will be a clean network error instead of a confusing `.filter is not a function`
   crash.

## 4. Close the loop: CORS

Go back to Render → your backend service → Environment → set `CORS_ORIGINS` to your real
frontend origin — e.g. `https://ai.alliedsoftwareengineers.com` if you're on a custom
domain, or `https://your-app.netlify.app` otherwise. **Exact match, no trailing slash** —
the browser's `Origin` header has to match this string exactly or CORS silently fails with
no `Access-Control-Allow-Origin` header on the response (the preflight to `/auth/login` etc.
just fails with no explanation in the Network tab). Then trigger a redeploy.

If you'd rather use a variable named `FRONTEND_URL` instead (some teams prefer that name by
convention), that also works — it's additive to `CORS_ORIGINS`, not a replacement, so either
one (or both) gets picked up.

## 5. Verify

- `curl https://ase-ai-backend.onrender.com/api/v1/health` → `{"status":"ok"}`
- Open your Netlify URL, register an account, send a message.
- If login seems to silently fail (e.g. `/auth/me` returns 401 even right after logging
  in): open browser dev tools → Network tab → check the register/login response actually
  sets cookies (Application tab → Cookies), and confirm `ENVIRONMENT=production` is set on
  the Render service (this alone makes cookies `SameSite=None`; see above) and
  `CORS_ORIGINS` exactly matches your Netlify URL (scheme + host, no trailing slash, no
  typos).

## Custom domains later

Both Netlify and Render support custom domains on free tiers. If you later point
`ai.alliedsoftwareengineers.com` at Netlify and an API subdomain at Render, update
`CORS_ORIGINS` and `VITE_API_URL` to match — nothing else changes.
