from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    _connect_args = {"check_same_thread": False}
    _pool_args = {}
else:
    # connect_timeout leaves room for a serverless DB (Neon) waking from idle
    _connect_args = {"connect_timeout": 15}
    _pool_args = {"pool_size": 5, "max_overflow": 5, "pool_recycle": 300}

engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args=_connect_args, **_pool_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
