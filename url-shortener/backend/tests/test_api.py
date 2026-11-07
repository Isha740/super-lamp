from app.config import settings
from app.database import SessionLocal
from app.models import Link
from app.services.clicks import flush_clicks

LONG = "https://example.com/some/really/long/path/to/an/article?id=12345&ref=newsletter"


def shorten(client, auth, url=LONG):
    return client.post("/api/links", json={"long_url": url}, headers=auth)


def test_requires_auth(client):
    assert client.post("/api/links", json={"long_url": LONG}).status_code == 401
    assert client.get("/api/links").status_code == 401


def test_register_login_errors(client):
    client.post("/api/auth/register", json={"username": "isha", "password": "password123"})
    dup = client.post("/api/auth/register", json={"username": "ISHA", "password": "password123"})
    assert dup.status_code == 409
    bad = client.post("/api/auth/login", json={"username": "isha", "password": "wrong-pass"})
    assert bad.status_code == 401


def test_short_url_not_shortened(client, auth):
    r = shorten(client, auth, "https://a.io")
    assert r.status_code == 400 and "already short enough" in r.json()["detail"]


def test_invalid_url(client, auth):
    assert shorten(client, auth, "ht!tp://bad url").status_code == 422


def test_shorten_creates_unique_code(client, auth):
    r = shorten(client, auth)
    assert r.status_code == 201
    body = r.json()
    assert len(body["short_code"]) == settings.code_length
    assert body["short_url"].endswith("/" + body["short_code"])
    assert body["clicks"] == 0


def test_same_url_same_code(client, auth):
    a = shorten(client, auth).json()["short_code"]
    b = shorten(client, auth).json()["short_code"]
    assert a == b
    assert len(client.get("/api/links", headers=auth).json()) == 1


def test_redirect_cache_and_counter(client, auth, fake_redis):
    code = shorten(client, auth).json()["short_code"]
    for _ in range(3):
        r = client.get(f"/{code}", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == LONG
    assert fake_redis.get(f"url:{code}") == LONG          # cached
    assert fake_redis.get(f"clicks:{code}") == "3"        # pending in redis
    assert client.get(f"/api/links/{code}/clicks", headers=auth).json()["clicks"] == 3


def test_flush_moves_counts_to_postgres_without_changing_total(client, auth, fake_redis):
    code = shorten(client, auth).json()["short_code"]
    for _ in range(5):
        client.get(f"/{code}", follow_redirects=False)
    with SessionLocal() as db:
        assert flush_clicks(db, fake_redis) == 5
        assert db.query(Link).filter_by(short_code=code).one().clicks == 5
    assert fake_redis.get(f"clicks:{code}") is None
    client.get(f"/{code}", follow_redirects=False)
    assert client.get(f"/api/links/{code}/clicks", headers=auth).json()["clicks"] == 6


def test_unknown_code_404(client):
    assert client.get("/Zzzzzzz", follow_redirects=False).status_code == 404


def test_users_are_isolated(client, auth):
    code = shorten(client, auth).json()["short_code"]
    client.post("/api/auth/register", json={"username": "other", "password": "password123"})
    tok = client.post("/api/auth/login", json={"username": "other", "password": "password123"}).json()["access_token"]
    other = {"Authorization": f"Bearer {tok}"}
    assert client.get(f"/api/links/{code}/clicks", headers=other).status_code == 404
    assert client.delete(f"/api/links/{code}", headers=other).status_code == 404
    assert client.get("/api/links", headers=other).json() == []


def test_delete_removes_link_and_cache(client, auth, fake_redis):
    code = shorten(client, auth).json()["short_code"]
    client.get(f"/{code}", follow_redirects=False)
    assert client.delete(f"/api/links/{code}", headers=auth).status_code == 204
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404


def test_rate_limit(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    assert shorten(client, auth).status_code == 201
    assert shorten(client, auth).status_code == 201
    assert shorten(client, auth).status_code == 429


def test_docs_not_shadowed_by_redirect(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}


def test_responses_are_never_cacheable(client, auth):
    code = shorten(client, auth).json()["short_code"]
    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.headers["cache-control"] == "no-store"
    assert client.get("/api/links", headers=auth).headers["cache-control"] == "no-store"
