# Shortly - URL Shortener

**Stack:** FastAPI (Python) - React (Vite) - PostgreSQL - Redis

## What it does
- Sign up / log in (bcrypt-hashed passwords, JWT auth)
- Paste a long URL -> **length check** (only shortened if the short link would actually be shorter)
- Generates a unique 7-character short code, stores `long_url <-> short_code` in PostgreSQL
- Visiting `/<code>` redirects and counts the click
- "View count" button shows the live click count for each link

## How Redis is used
| Purpose | Redis key | Why |
|---|---|---|
| Redirect cache | `url:<code>` (TTL 1h) | most redirects never touch Postgres |
| Click counter | `clicks:<code>` (INCR) | atomic and very fast; no DB write per click |
| Rate limit | `rl:shorten:<user>:<minute>` | max 30 shorten requests/user/minute |

A background worker moves pending counters into Postgres every 5 seconds
(`GETDEL` then `UPDATE ... clicks = clicks + n`), and once more on shutdown.
Total shown to the user = Postgres count + pending Redis count, so it is always current.
If Redis is down, redirects still work and fall back to counting directly in Postgres.

## Workflow
```
Register -> Login (JWT)
   |
POST /api/links {long_url}
   1. normalize (add https://) + validate (http/https, max 2048 chars)
   2. reject if it is already one of our short links
   3. length check: len(long_url) > len(BASE_URL) + 1 + 7 ?   no -> 400 "already short enough"
   4. same user + same URL already stored? -> return existing code
   5. random base62 code -> INSERT (UNIQUE) -> retry on collision
   6. return short_url

GET /<code>
   Redis cache (miss -> Postgres, then cache) -> INCR clicks:<code> -> 302 redirect

GET /api/links/<code>/clicks  -> postgres clicks + pending redis clicks
```

## API
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | no | create account |
| POST | /api/auth/login | no | returns JWT |
| GET | /api/auth/me | yes | current user |
| POST | /api/links | yes | shorten a URL |
| GET | /api/links | yes | list your links |
| GET | /api/links/{code}/clicks | yes | click count |
| DELETE | /api/links/{code} | yes | delete a link |
| GET | /{code} | no | redirect + count |
| GET | /api/health | no | health check |

Interactive docs: http://localhost:8000/docs

## Run it

### Option A - everything in Docker (one command)
Requires Docker Desktop.
```bash
docker compose up --build
```
Open **http://localhost:8080**. (API docs at http://localhost:8000/docs)

### Option B - development mode (hot reload)
Run only Postgres and Redis in Docker, and the backend/frontend on your machine.

```bash
# 1) databases
docker compose up -d postgres redis

# 2) backend  (terminal 1)
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload     # http://localhost:8000

# 3) frontend (terminal 2)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```
In this mode short links look like `http://localhost:8000/<code>` (served by the backend directly).

If you already run Postgres/Redis locally on 5432/6379, either stop them or change the
host ports in `docker-compose.yml` and set `DATABASE_URL` / `REDIS_URL` in `backend/.env`.

## Tests
```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```
Tests use SQLite and fakeredis, so they need no running services.

## Configuration (env vars, see backend/app/config.py)
`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `BASE_URL`, `CORS_ORIGINS`, `CODE_LENGTH`,
`MAX_URL_LENGTH`, `CACHE_TTL_SECONDS`, `FLUSH_INTERVAL_SECONDS`, `RATE_LIMIT_PER_MINUTE`.
If you change `CODE_LENGTH`, update the `{7}` in `frontend/nginx.conf` too.

## Project layout
```
url-shortener/
  docker-compose.yml
  .env.example
  backend/
    app/
      main.py            app, lifespan, background click flusher
      config.py          settings
      database.py  models.py  schemas.py  security.py  deps.py  redis_client.py
      routers/           auth.py  links.py  redirect.py
      services/          shortener.py (validation, length check, codes)  clicks.py (redis counters)
    tests/
    Dockerfile  requirements*.txt
  frontend/
    src/                 App.jsx  api.js  components/  styles.css
    Dockerfile  nginx.conf  vite.config.js
```

## Before going to production
Set a long random `SECRET_KEY` and `POSTGRES_PASSWORD`, set `BASE_URL` to your real domain,
serve over HTTPS, and switch `create_all` to Alembic migrations once the schema starts changing.
