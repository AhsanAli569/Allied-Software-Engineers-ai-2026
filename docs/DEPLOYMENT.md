# ASE AI — Production Deployment (Linux VPS + Docker)

This assumes a fresh Ubuntu 22.04/24.04 VPS you control (DigitalOcean, Hetzner, Linode,
AWS EC2, etc.) and the domain `ai.alliedsoftwareengineers.com` pointed at it. Docker works
fine here even though it doesn't run on the Windows dev machine this was built on — that
was a local virtualization/Hyper-V issue specific to that machine, not a project constraint.

## 1. Provision the server

- Ubuntu 22.04 or 24.04, at least 2 vCPU / 4GB RAM to start.
- Open inbound ports **80** and **443** (and 22 for SSH) in your provider's firewall/security group.
- Install Docker Engine + the Compose plugin:
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER   # log out/in after this
  docker compose version          # sanity check
  ```

## 2. DNS

Create an **A record** for `ai.alliedsoftwareengineers.com` pointing at the server's public
IP. Wait for it to propagate (`dig ai.alliedsoftwareengineers.com`) before requesting a
certificate in step 5 — Let's Encrypt needs the domain to actually resolve to this server.

## 3. Get the code onto the server

```bash
git clone <your-repo-url> ase-ai
cd ase-ai
```

## 4. Configure environment

```bash
cp .env.production.example .env          # Postgres credentials for docker compose
cp backend/.env.example backend/.env      # app secrets
```

Edit `.env` (repo root): set a real `POSTGRES_PASSWORD`.

Edit `backend/.env`:
- `JWT_SECRET` — generate with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` — whichever you have
- `CORS_ORIGINS=https://ai.alliedsoftwareengineers.com`
- Leave `DATABASE_URL` as-is — `docker-compose.prod.yml` overrides it to point at the `db`
  container using the root `.env`'s Postgres credentials.

Neither `.env` file is committed to git (see `.gitignore`) — they only ever live on the server.

## 5. First-time HTTPS certificate (one-time bootstrap)

The production nginx config expects certificate files that don't exist yet, so bring the
stack up with the HTTP-only bootstrap config first:

```bash
docker compose -f docker-compose.prod.yml up -d db backend
# temporarily point nginx at the HTTP-only bootstrap config
sed -i 's#\./frontend/deploy/nginx.conf:#./frontend/deploy/nginx.bootstrap.conf:#' docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d web

# request the real certificate (replace the email address)
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d ai.alliedsoftwareengineers.com \
  --email you@alliedsoftwareengineers.com --agree-tos --no-eff-email

# switch nginx back to the real HTTPS config
git checkout docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```

## 6. Bring up the full stack

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

The `certbot` service stays running and checks for renewal every 12 hours (Let's Encrypt
certs are valid 90 days; certbot only actually renews when it's within 30 days of expiry).

## 7. Create the first administrator

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.cli create-admin
```

## 8. Verify

```bash
curl https://ai.alliedsoftwareengineers.com/api/v1/health
```
Then open `https://ai.alliedsoftwareengineers.com` in a browser and register/log in.

## Redeploying after code changes

```bash
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```
Database migrations run automatically on backend container start (`entrypoint.sh`).

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f web
```

## Database backups

A basic daily dump via cron (adjust retention/off-server storage as you see fit —
"a backup is not trustworthy until restoration has been tested," so periodically verify
you can actually restore one):

```bash
# /etc/cron.d/ase-ai-backup
0 3 * * * root cd /path/to/ase-ai && docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U ase_ai ase_ai | gzip > /var/backups/ase-ai-$(date +\%F).sql.gz
```

Uploaded files (images/documents) live on disk in the `backend-storage` Docker volume, not
in the database — back that up too, e.g.:

```bash
docker run --rm -v alliedsoftwareengineersai_backend-storage:/data -v /var/backups:/backup \
  alpine tar czf /backup/ase-ai-storage-$(date +%F).tar.gz -C /data .
```

## HSTS

`frontend/deploy/nginx.conf` has the `Strict-Transport-Security` header commented out.
Enable it only after you've confirmed HTTPS is working reliably for a while — browsers
cache HSTS aggressively, so it's hard to undo if something's misconfigured.
