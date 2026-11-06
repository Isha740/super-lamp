import os
import tempfile

# Must be set before the app is imported
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ENABLE_BACKGROUND_FLUSH"] = "false"
os.environ["BASE_URL"] = "http://localhost:8000"

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.redis_client import get_redis  # noqa: E402


@pytest.fixture
def fake_redis():
    r = fakeredis.FakeRedis(decode_responses=True)
    yield r
    r.flushall()


@pytest.fixture
def client(fake_redis):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    client.post("/api/auth/register", json={"username": "isha", "password": "password123"})
    token = client.post("/api/auth/login", json={"username": "isha", "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
