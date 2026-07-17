# Deploying the LandVille backend (free tier)

Django + DRF + Channels (websockets). Prepped to run on **free** services with
no credentials committed — `.env` is gitignored; secrets live in the host
dashboard.

## Recommended free stack

| Piece | Service | Notes |
|-------|---------|-------|
| Web (API + websockets) | **Render** free Web Service | Runs `daphne` (ASGI). Spins down after ~15 min idle, cold-starts on next request. |
| Database | **Neon** free Postgres | Persistent free tier (Render's own free Postgres expires). |
| Redis | **not needed** | Channels falls back to an in-memory layer and Celery runs tasks inline (see below). Add **Upstash** free Redis later if you want a real worker. |

### Why no Redis / worker on free tier
`settings.py` uses an in-memory channel layer when `REDIS_URL` is unset, and
sets `CELERY_TASK_ALWAYS_EAGER=True` in the same case — so email notifications
run synchronously inside the web process. One free web service is enough. This
works because a single instance serves all websocket connections; if you ever
scale to more than one instance, add Redis (`REDIS_URL`) so they share state.

## Deploy steps (Render + Neon)

1. **Database** — create a free project at [neon.tech], copy the connection
   string (looks like `postgres://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`).
2. **Push** this repo to GitHub.
3. **Render** → *New +* → *Blueprint* → select the repo. Render reads
   `render.yaml` and creates the `landville-backend` web service.
4. **Set the secret env vars** in the Render dashboard (the `sync: false` ones):
   - `DATABASE_URL` = the Neon string
   - `ALLOWED_HOSTS` = `landville-backend.onrender.com` (your Render URL)
   - `CORS_WHITELIST` = your frontend URL, e.g. `https://landville-frontend.onrender.com`
   - `CSRF_TRUSTED_ORIGINS` = same frontend URL
   - `FRONT_END_URL` = same frontend URL
   - `DOMAIN` = `https://landville-backend.onrender.com`
   - `DEFAULT_FROM_EMAIL` = e.g. `no-reply@yourdomain`

   `SECRET_KEY` is generated automatically; `DEBUG=False` and the security
   flags are already set in `render.yaml`.
5. **Deploy.** The build installs deps + runs `collectstatic`; the start command
   runs `migrate` then launches `daphne`. Seed data (optional):
   open the Render *Shell* and run `python load_fixtures.py`.
6. **Create an admin** (optional): in the Render Shell, `python manage.py createsuperuser`.

Health check is `/api/v1/properties/` (public, returns 200).

## Docker (portable alternative)

A `Dockerfile` is included for hosts that take an image (Fly.io, Koyeb,
Railway, or self-hosting):

```bash
docker build -t landville-backend .
docker run -p 8000:8000 --env-file .env landville-backend
```

## Local run

```bash
cp .env.example .env      # then fill in real values (stays gitignored)
source .env
pip install -r requirements.txt
python manage.py migrate && python load_fixtures.py
daphne -b 0.0.0.0 -p 8000 landville.asgi:application
```

## Secrets policy
Never commit real values. `.env` is gitignored; `.env.example` holds
placeholders only. Production secrets belong in the host's env-var settings.

[neon.tech]: https://neon.tech
