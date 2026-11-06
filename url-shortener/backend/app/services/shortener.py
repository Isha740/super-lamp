"""URL validation, the 'does it need shortening?' check, and unique code creation."""
import hashlib
import secrets
import string
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Link

ALPHABET = string.ascii_letters + string.digits  # base62


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if raw and "://" not in raw:
        raw = "https://" + raw
    return raw


def validate_url(url: str, max_len: int) -> str | None:
    if not url:
        return "Please enter a URL."
    if len(url) > max_len:
        return f"URL is too long (max {max_len} characters)."
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or " " in url:
        return "Enter a valid http(s) URL."
    return None


def short_url_length(base_url: str, code_length: int) -> int:
    return len(base_url.rstrip("/")) + 1 + code_length


def needs_shortening(long_url: str, base_url: str, code_length: int) -> bool:
    """Only shorten when the resulting short link would really be shorter."""
    return len(long_url) > short_url_length(base_url, code_length)


def is_own_short_url(url: str, base_url: str) -> bool:
    return url.startswith(base_url.rstrip("/") + "/")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def generate_code(length: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_link(db: Session, user_id: int, long_url: str, code_length: int, attempts: int = 10) -> Link:
    """Uniqueness is guaranteed by the DB UNIQUE constraint; retry on collision.
    If this user already shortened this URL, return the existing link."""
    h = url_hash(long_url)
    for _ in range(attempts):
        link = Link(user_id=user_id, long_url=long_url, url_hash=h,
                    short_code=generate_code(code_length))
        db.add(link)
        try:
            db.commit()
            return link
        except IntegrityError:
            db.rollback()
            existing = db.scalar(select(Link).where(Link.user_id == user_id, Link.url_hash == h))
            if existing:
                return existing
    raise RuntimeError("Could not generate a unique short code")
