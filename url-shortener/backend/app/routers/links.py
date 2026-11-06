import time

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Link, User
from ..redis_client import get_redis
from ..schemas import ClickStats, LinkIn, LinkOut
from ..services import shortener
from ..services.clicks import CLICK_PREFIX, URL_PREFIX, pending_clicks

router = APIRouter(prefix="/api/links", tags=["links"])


def _out(link: Link, pending: int = 0) -> LinkOut:
    return LinkOut(
        short_code=link.short_code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.short_code}",
        long_url=link.long_url,
        clicks=link.clicks + pending,
        created_at=link.created_at,
    )


def _rate_limit(r: Redis, user_id: int) -> None:
    """Fixed-window limiter: N shorten requests / user / minute. Fails open if Redis is down."""
    key = f"rl:shorten:{user_id}:{int(time.time() // 60)}"
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, 65)
    except RedisError:
        return
    if count > settings.rate_limit_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Slow down a little.")


def _owned(db: Session, user: User, code: str) -> Link:
    link = db.scalar(select(Link).where(Link.short_code == code, Link.user_id == user.id))
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found.")
    return link


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
def create_short_link(
    payload: LinkIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    _rate_limit(r, user.id)

    long_url = shortener.normalize_url(payload.long_url)
    error = shortener.validate_url(long_url, settings.max_url_length)
    if error:
        raise HTTPException(422, error)
    if shortener.is_own_short_url(long_url, settings.base_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That is already a short link from this service.")
    # Length check: is shortening actually worthwhile?
    if not shortener.needs_shortening(long_url, settings.base_url, settings.code_length):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This URL is already short enough - no need to shorten it.")

    link = shortener.create_link(db, user.id, long_url, settings.code_length)
    return _out(link, pending_clicks(r, [link.short_code]).get(link.short_code, 0))


@router.get("", response_model=list[LinkOut])
def list_links(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    links = db.scalars(select(Link).where(Link.user_id == user.id).order_by(Link.id.desc())).all()
    pending = pending_clicks(r, [l.short_code for l in links])
    return [_out(l, pending.get(l.short_code, 0)) for l in links]


@router.get("/{code}/clicks", response_model=ClickStats)
def view_click_count(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    link = _owned(db, user, code)
    total = link.clicks + pending_clicks(r, [code]).get(code, 0)
    return ClickStats(short_code=code, clicks=total)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    link = _owned(db, user, code)
    db.execute(delete(Link).where(Link.id == link.id))
    db.commit()
    try:
        r.delete(URL_PREFIX + code, CLICK_PREFIX + code)
    except RedisError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
