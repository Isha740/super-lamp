"""Click counting with Redis.

Hot path:  every redirect does an atomic Redis INCR on  clicks:<code>.
Background: a worker moves those pending counts into Postgres (atomic GETDEL,
then UPDATE links SET clicks = clicks + n).  Total clicks = Postgres + pending.
"""
import logging

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models import Link

log = logging.getLogger(__name__)

CLICK_PREFIX = "clicks:"
URL_PREFIX = "url:"


def pending_clicks(r: Redis, codes: list[str]) -> dict[str, int]:
    if not codes:
        return {}
    try:
        values = r.mget([CLICK_PREFIX + c for c in codes])
        return {c: int(v or 0) for c, v in zip(codes, values)}
    except RedisError:
        return {c: 0 for c in codes}


def flush_clicks(db: Session, r: Redis) -> int:
    """Move pending Redis counters into Postgres. Safe to run from many workers:
    GETDEL is atomic, so each increment is flushed exactly once."""
    flushed = 0
    for key in r.scan_iter(match=CLICK_PREFIX + "*", count=500):
        raw = r.getdel(key)
        if not raw:
            continue
        n = int(raw)
        code = key[len(CLICK_PREFIX):]
        try:
            db.execute(update(Link).where(Link.short_code == code).values(clicks=Link.clicks + n))
            db.commit()
            flushed += n
        except Exception:
            db.rollback()
            r.incrby(key, n)  # put it back so nothing is lost
            raise
    return flushed
