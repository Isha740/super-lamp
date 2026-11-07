# Deploying Shortly (free combo)

**Vercel** (React) + **Render** (FastAPI) + **Neon** (PostgreSQL) + **Upstash** (Redis)

```
Browser --> Vercel (React app)
              |-- /api/*       --proxy--> Render (FastAPI) --> Neon (Postgres)
              '-- /<7 chars>   --proxy--> Render (redirect)  --> Upstash (Redis)
```
Because Vercel proxies `/api` and short codes to Render, the browser only talks to ONE domain:
no CORS setup, and short links look like `https://your-app.vercel.app/aB3dE9x`.

## Free-tier facts (checked Nov 2026 - limits change, re-check if something breaks)
| Service | Free limit that matters here |
|---|---|
| Render web service | sleeps after 15 min without traffic; wake-up takes about a minute; 750 free instance hours/month |
| Neon Postgres | compute suspends after 5 min idle and wakes on the next query; roughly 0.5-1 GB storage |
| Upstash Redis | 256 MB, **500,000 commands/month** (this is why `FLUSH_INTERVAL_SECONDS=120`) |
| Vercel | free Hobby plan, meant for personal projects |

## Step 0 - Push the project to GitHub
From your repo root (the folder that contains `url-shortener/`):
```powershell
git status                      # should NOT list node_modules, venv or .env
git add url-shortener
git commit -m "Add URL shortener project"
git push
```
Render and Vercel both deploy from this GitHub repo.

## Step 1 - Neon (PostgreSQL)
1. Sign up at neon.com, create a project. Pick the region nearest to you and use the same
   area for Render later (fewer milliseconds per query).
2. On the dashboard click **Connect** and copy the connection string (the "pooled" one is fine).
   It looks like `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`.
   Paste it as-is; the app adds the driver prefix itself.
3. If the backend later complains about `channel_binding`, delete `&channel_binding=require` from the string.

## Step 2 - Upstash (Redis)
1. Sign up at upstash.com, create a **Redis** database (free plan), same area as the others.
2. Copy the **TCP** connection URL that starts with `rediss://` (two s's = TLS):
   `rediss://default:PASSWORD@xxxx.upstash.io:6379`.
   (Do NOT use the REST URL / REST token - this app uses the normal Redis protocol.)

## Step 3 - Render (backend)
1. Sign up at render.com, **New > Web Service**, connect GitHub and pick your repo.
2. Settings:
   - **Language:** Docker
   - **Root Directory:** `url-shortener/backend`   (Dockerfile Path stays `./Dockerfile`)
   - **Instance type:** Free
   - **Health Check Path:** `/api/health`
3. **Environment variables:**
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from Step 1 |
   | `REDIS_URL` | the Upstash `rediss://` URL from Step 2 |
   | `SECRET_KEY` | a long random string, generate one with: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `FLUSH_INTERVAL_SECONDS` | `120` |
   | `BASE_URL` | `https://placeholder.vercel.app` (temporary, fixed in Step 5) |
4. Deploy. When it is live, open `https://<your-service>.onrender.com/api/health` (should show
   `{"status":"ok"}`; the first hit may take up to a minute) and `/docs`.
   Copy the service URL.

## Step 4 - Vercel (frontend)
1. Open `url-shortener/frontend/vercel.json` and replace both `YOUR-API-NAME.onrender.com`
   with your real Render host (e.g. `shortly-api-xyz.onrender.com`, no trailing slash).
2. Commit and push:
   ```powershell
   git add url-shortener
   git commit -m "Point Vercel rewrites at Render"
   git push
   ```
3. On vercel.com: **Add New > Project**, import the repo, set **Root Directory** to
   `url-shortener/frontend` (framework should auto-detect as Vite), leave env vars empty, Deploy.
4. Copy your site URL, e.g. `https://shortly-abc.vercel.app`.

## Step 5 - Tell the backend its public address
In Render > your service > Environment, set `BASE_URL` to the Vercel URL
(`https://shortly-abc.vercel.app`, no trailing slash) and save. Render redeploys.

## Step 6 - Test
1. Open the Vercel URL, register, log in.
2. Paste a short URL like `https://a.io` -> should say it is already short enough.
3. Paste a long URL -> you get `https://<your-vercel-domain>/<7 chars>`.
4. Open the short link a few times, then click **View count**.

## Things to expect on the free plan
- **First request after 15 idle minutes is slow** (Render waking up, about a minute).
  The very first click on a short link after a quiet spell will be slow too.
  I could not confirm how long Vercel's proxy waits on a slow upstream, so if you see a 504 on the
  first request, just reload.
- **Optional keep-awake:** a free uptime monitor (UptimeRobot, cron-job.org) that calls
  `https://<your-service>.onrender.com/api/health` every 10 minutes keeps Render awake.
  Always-on for a month is about 720-744 hours, which fits inside the 750 free hours
  as long as this is your only free Render service.
- Neon wakes from idle in about a second or so on the first query; the app already tolerates that.
- Render may restart a free service at any time. Pending click counts live in Redis, so they survive.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Short links show the wrong domain | `BASE_URL` on Render not set to the Vercel URL (Step 5) |
| Register/login shows "Cannot reach the server" | `vercel.json` still has `YOUR-API-NAME`, or Render is asleep: wait a minute, reload |
| Backend crashes on start with an SSL / connection error | check `DATABASE_URL` (Step 1.3) and that `REDIS_URL` starts with `rediss://` |
| Clicks never appear | `REDIS_URL` wrong; check Render logs for Redis errors |
| Upstash says quota exceeded | lower traffic or raise `FLUSH_INTERVAL_SECONDS` |
| Short link 404 right after creating | the link was created on a different `BASE_URL`/DB; check Render env vars |
