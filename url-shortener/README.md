# Shortly - URL Shortener

A full-stack URL shortener with user accounts, a length check before shortening, unique short codes, and per-link click counts.

**Live app: https://super-lamp.vercel.app**

> The backend runs on a free plan that sleeps when idle. The first request after a quiet period can take up to a minute; reload if it times out.

## Features

- Sign up and log in (bcrypt-hashed passwords, JWT authentication)
- Paste a long URL and get a unique 7-character short link
- Length check: a URL is only shortened if the short link would actually be shorter
- Short links redirect and count every click
- "View count" shows the live click total for each link
- Copy and delete your links; each user only sees their own
- Rate limiting (30 shorten requests per user per minute)
- Responsive layout

## Tech stack

| Layer | Technology | Hosted on |
|---|---|---|
| Frontend | React + Vite | Vercel |
| Backend | FastAPI (Python) | Render |
| Database | PostgreSQL | Neon |
| Cache and counters | Redis | Upstash |
| Local development | Docker Compose | your machine |

## How it works

```
Browser
  |
  v
React app (Vercel) -- /api/* and /<code> --> FastAPI (Render) --> PostgreSQL (Neon)
                                                  |
                                                  +--> Redis (Upstash)
```

Shortening a link (`POST /api/links`):
1. The URL is normalized (adds `https://` if missing) and validated (http/https only, max 2048 characters).
2. Links that already point at this service are rejected.
3. Length check: the URL must be longer than `len(BASE_URL) + 1 + 7`, otherwise it is "already short enough".
4. If you already shortened this URL, the existing code is returned.
5. A random base62 code is inserted. The database's UNIQUE constraint guarantees uniqueness, and the insert is retried on the rare collision.

Opening a short link (`GET /<code>`):
1. The target URL is read from the Redis cache (falling back to PostgreSQL, then cached for an hour).
2. The click is counted with an atomic Redis `INCR`.
3. The user is redirected with HTTP 302 (not 301, so browsers don't cache it and every click is counted).

Click counting:
- Redis absorbs clicks, so there is no database write per visit.
- A background worker moves pending counts into PostgreSQL in batches (atomic `GETDEL`, then `UPDATE ... clicks = clicks + n`), and once more on shutdown.
- The count shown to the user is the PostgreSQL total plus pending Redis clicks, so it is always current.
- If Redis is unavailable, redirects still work and count directly in PostgreSQL.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | no | create an account |
| POST | `/api/auth/login` | no | returns a JWT |
| GET | `/api/auth/me` | yes | current user |
| POST | `/api/links` | yes | shorten a URL |
| GET | `/api/links` | yes | list your links |
| GET | `/api/links/{code}/clicks` | yes | click count for a link |
| DELETE | `/api/links/{code}` | yes | delete a link |
| GET | `/{code}` | no | redirect and count |
| GET | `/api/health` | no | health check |

Interactive API docs (Swagger) are available at `/docs` on the backend.

## Run locally

Requires Docker Desktop.

### Option A: everything in Docker
```bash
docker compose up --build
```
Open http://localhost:8080 (API docs at http://localhost:8000/docs).

### Option B: development mode with hot reload
```bash
# 1) databases only
docker compose up -d postgres redis

# 2) backend (terminal 1)
cd backend
python -m venv venv
source venv/bin/activate            # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload       # http://localhost:8000

# 3) frontend (terminal 2)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Stop everything with `docker compose down`.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```
The 16 tests use SQLite and fakeredis, so no running services are needed. They cover authentication, the length check, unique codes, redirect caching and counting, the Redis-to-PostgreSQL flush, user isolation, deletion, rate limiting and response headers.

## Deployment

The live app uses free tiers of four services. Full step-by-step instructions are in [DEPLOY.md](DEPLOY.md).

| Service | Role | Key settings |
|---|---|---|
| Neon | PostgreSQL | `DATABASE_URL` |
| Upstash | Redis | `REDIS_URL` (TLS, `rediss://`) |
| Render | FastAPI backend (Docker) | Root Directory `url-shortener/backend`, health check `/api/health` |
| Vercel | React frontend | Root Directory `url-shortener/frontend` |

`frontend/vercel.json` proxies `/api/*` and 7-character short codes to the Render backend, so the browser talks to a single domain (no CORS setup) and short links look like `https://super-lamp.vercel.app/aB3dE9x`.

Backend environment variables on Render:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon connection string |
| `REDIS_URL` | Upstash `rediss://` URL |
| `SECRET_KEY` | long random string |
| `BASE_URL` | `https://super-lamp.vercel.app` |
| `FLUSH_INTERVAL_SECONDS` | `120` (keeps within Upstash's free command quota) |

Every `git push` to the repository redeploys both the backend and the frontend automatically.

## Configuration

Set through environment variables (see `backend/app/config.py`): `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `BASE_URL`, `CORS_ORIGINS`, `CODE_LENGTH`, `MAX_URL_LENGTH`, `CACHE_TTL_SECONDS`, `FLUSH_INTERVAL_SECONDS`, `RATE_LIMIT_PER_MINUTE`.

If you change `CODE_LENGTH`, also update the `{7}` pattern in `frontend/nginx.conf` and `frontend/vercel.json`.

## Project structure

```
url-shortener/
  docker-compose.yml        local Postgres + Redis + backend + frontend
  DEPLOY.md                 deployment guide
  backend/
    app/
      main.py               app setup, background click flusher, no-store headers
      config.py             settings from environment variables
      database.py  models.py  schemas.py  security.py  deps.py  redis_client.py
      routers/
        auth.py             register, login, current user
        links.py            create, list, count, delete
        redirect.py         public redirect + click counting
      services/
        shortener.py        validation, length check, code generation
        clicks.py           Redis counters and flush to PostgreSQL
    tests/
    Dockerfile  requirements.txt  requirements-dev.txt
  frontend/
    src/
      App.jsx  api.js  styles.css
      components/           AuthForm.jsx  Dashboard.jsx
    Dockerfile  nginx.conf  vercel.json  vite.config.js
```

## Known limitations

- Database tables are created automatically at startup; switch to Alembic migrations as the schema grows.
- Login tokens last 24 hours and are stored in `localStorage`; there is no refresh flow.
- Rate limiting uses a simple fixed one-minute window.
- On the free hosting plans the backend sleeps after 15 idle minutes, and the database pauses after 5.
