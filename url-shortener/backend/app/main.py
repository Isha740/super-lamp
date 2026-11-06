import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .redis_client import get_redis
from .routers import auth, links, redirect
from .services.clicks import flush_clicks

log = logging.getLogger("shortener")


def _flush_loop(stop: threading.Event) -> None:
    r = get_redis()
    while not stop.wait(settings.flush_interval_seconds):
        try:
            with SessionLocal() as db:
                flush_clicks(db, r)
        except Exception:
            log.exception("click flush failed; will retry")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)   # swap for Alembic migrations when the schema grows
    stop = threading.Event()
    worker = None
    if settings.enable_background_flush:
        worker = threading.Thread(target=_flush_loop, args=(stop,), daemon=True)
        worker.start()
    yield
    if worker:
        stop.set()
        worker.join(timeout=5)
        try:
            with SessionLocal() as db:
                flush_clicks(db, get_redis())   # don't lose pending clicks on shutdown
        except Exception:
            log.exception("final click flush failed")


app = FastAPI(title="Shortly - URL Shortener API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(links.router)
app.include_router(redirect.router)   # keep last: it owns the catch-all /{code}
