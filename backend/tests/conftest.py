from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client() -> Iterator[TestClient]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client: TestClient, email: str = "owner@example.com", business: str = "Bella Hair Studio") -> dict:
    r = client.post(
        "/api/auth/register",
        json={"name": "Owner", "email": email, "password": "s3cret-pass", "business_name": business},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def owner(client: TestClient) -> dict:
    return register(client)


@pytest.fixture
def next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


@pytest.fixture
def setup_business(client: TestClient, owner: dict) -> dict:
    """Business open Mon-Fri 09:00-12:00 with a 60-minute haircut."""
    hours = [{"weekday": d, "opens_at": "09:00", "closes_at": "12:00"} for d in range(5)]
    assert client.put("/api/hours", json=hours, headers=owner).status_code == 200
    svc = client.post(
        "/api/services", json={"name": "Haircut", "duration_minutes": 60, "price_cents": 4500}, headers=owner
    ).json()
    slug = client.get("/api/auth/me", headers=owner).json()["business"]["slug"]
    return {"headers": owner, "service_id": svc["id"], "slug": slug}
