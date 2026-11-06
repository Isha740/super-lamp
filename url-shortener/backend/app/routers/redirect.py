from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import RedirectResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Link
from ..redis_client import get_redis
from ..services.clicks import CLICK_PREFIX, URL_PREFIX

router = APIRouter()


@router.get("/{code}", include_in_schema=False)
def follow_short_link(
    code: str = Path(pattern=r"^[A-Za-z0-9]{4,16}$"),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    """Public redirect. Redis cache for the lookup, Redis INCR for the counter.
    If Redis is unavailable we degrade gracefully to Postgres only."""
    redis_ok = True
    long_url = None
    try:
        long_url = r.get(URL_PREFIX + code)
    except RedisError:
        redis_ok = False

    if long_url is None:
        long_url = db.scalar(select(Link.long_url).where(Link.short_code == code))
        if long_url is None:
            raise HTTPException(404, "Short link not found.")
        if redis_ok:
            try:
                r.set(URL_PREFIX + code, long_url, ex=settings.cache_ttl_seconds)
            except RedisError:
                redis_ok = False

    if redis_ok:
        try:
            r.incr(CLICK_PREFIX + code)
        except RedisError:
            redis_ok = False
    if not redis_ok:
        db.execute(update(Link).where(Link.short_code == code).values(clicks=Link.clicks + 1))
        db.commit()

    return RedirectResponse(long_url, status_code=302)
