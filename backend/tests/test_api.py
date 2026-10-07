from datetime import datetime, timedelta

from tests.conftest import register


def book(client, ctx, start: datetime, email="ana@example.com"):
    return client.post(
        f"/api/public/{ctx['slug']}/appointments",
        json={
            "service_id": ctx["service_id"],
            "start_at": start.isoformat(),
            "customer_name": "Ana Lima",
            "customer_email": email,
            "customer_phone": "+55 11 98765-4321",
        },
    )


# --- auth
def test_register_login_and_me(client):
    register(client, "maria@example.com", "Café & Co.")
    r = client.post("/api/auth/login", data={"username": "MARIA@example.com", "password": "s3cret-pass"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["email"] == "maria@example.com"
    assert me["business"]["slug"] == "cafe-co"


def test_duplicate_email_and_wrong_password(client):
    register(client)
    r = client.post(
        "/api/auth/register",
        json={"name": "Xavier", "email": "owner@example.com", "password": "another-pass", "business_name": "Other"},
    )
    assert r.status_code == 409
    assert client.post("/api/auth/login", data={"username": "owner@example.com", "password": "nope"}).status_code == 401


def test_slugs_are_unique(client):
    register(client, "a@example.com", "Barber Shop")
    h2 = register(client, "b@example.com", "Barber Shop")
    assert client.get("/api/auth/me", headers=h2).json()["business"]["slug"] == "barber-shop-2"


def test_protected_routes_require_token(client):
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/services", headers={"Authorization": "Bearer garbage"}).status_code == 401


# --- booking flow
def test_public_page_and_slots(client, setup_business, next_monday):
    page = client.get(f"/api/public/{setup_business['slug']}").json()
    assert page["name"] == "Bella Hair Studio"
    assert [s["name"] for s in page["services"]] == ["Haircut"]
    r = client.get(
        f"/api/public/{setup_business['slug']}/slots",
        params={"service_id": setup_business["service_id"], "date": next_monday.isoformat()},
    )
    assert r.json()["slots"] == ["09:00", "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00"]


def test_closed_day_returns_no_slots(client, setup_business, next_monday):
    sunday = next_monday + timedelta(days=6)
    r = client.get(
        f"/api/public/{setup_business['slug']}/slots",
        params={"service_id": setup_business["service_id"], "date": sunday.isoformat()},
    )
    assert r.json()["slots"] == []


def test_booking_blocks_overlapping_slots(client, setup_business, next_monday):
    start = datetime.combine(next_monday, datetime.min.time()).replace(hour=10)
    r = book(client, setup_business, start)
    assert r.status_code == 201, r.text
    assert r.json()["price_cents"] == 4500
    assert r.json()["end_at"].startswith(f"{next_monday.isoformat()}T11:00")

    params = {"service_id": setup_business["service_id"], "date": next_monday.isoformat()}
    slots = client.get(f"/api/public/{setup_business['slug']}/slots", params=params).json()["slots"]
    assert slots == ["09:00", "11:00"]  # 09:15-10:45 would overlap 10:00-11:00

    # same time and partially overlapping time are rejected
    assert book(client, setup_business, start, "bob@example.com").status_code == 409
    assert book(client, setup_business, start + timedelta(minutes=30), "bob@example.com").status_code == 409


def test_cannot_book_outside_hours_or_in_the_past(client, setup_business, next_monday):
    late = datetime.combine(next_monday, datetime.min.time()).replace(hour=11, minute=30)
    assert book(client, setup_business, late).status_code == 409  # would end 12:30, after closing
    assert book(client, setup_business, datetime.now() - timedelta(days=1)).status_code == 409


def test_cancelling_frees_the_slot(client, setup_business, next_monday):
    start = datetime.combine(next_monday, datetime.min.time()).replace(hour=9)
    appt = book(client, setup_business, start).json()
    r = client.patch(f"/api/appointments/{appt['id']}", json={"status": "cancelled"}, headers=setup_business["headers"])
    assert r.json()["status"] == "cancelled"
    assert book(client, setup_business, start, "other@example.com").status_code == 201


def test_owner_lists_appointments_and_sees_stats(client, setup_business, next_monday):
    base = datetime.combine(next_monday, datetime.min.time())
    book(client, setup_business, base.replace(hour=9))
    book(client, setup_business, base.replace(hour=10), "b@example.com")
    r = client.get(
        "/api/appointments",
        headers=setup_business["headers"],
        params={"start": next_monday.isoformat(), "end": next_monday.isoformat()},
    )
    assert [a["customer_email"] for a in r.json()] == ["ana@example.com", "b@example.com"]
    stats = client.get("/api/stats", headers=setup_business["headers"]).json()
    assert stats["next_7_days"] == 2


# --- isolation between businesses
def test_owner_cannot_touch_another_business(client, setup_business, next_monday):
    appt = book(client, setup_business, datetime.combine(next_monday, datetime.min.time()).replace(hour=9)).json()
    intruder = register(client, "intruder@example.com", "Other Biz")
    assert (
        client.patch(f"/api/appointments/{appt['id']}", json={"status": "cancelled"}, headers=intruder).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/services/{setup_business['service_id']}",
            headers=intruder,
            json={"name": "Hacked", "duration_minutes": 10, "price_cents": 0},
        ).status_code
        == 404
    )
    listed = client.get(
        "/api/appointments", headers=intruder, params={"start": next_monday.isoformat(), "end": next_monday.isoformat()}
    ).json()
    assert listed == []


def test_deactivated_service_cannot_be_booked(client, setup_business, next_monday):
    client.delete(f"/api/services/{setup_business['service_id']}", headers=setup_business["headers"])
    start = datetime.combine(next_monday, datetime.min.time()).replace(hour=9)
    assert book(client, setup_business, start).status_code == 404


def test_invalid_hours_are_rejected(client, owner):
    r = client.put("/api/hours", headers=owner, json=[{"weekday": 0, "opens_at": "18:00", "closes_at": "09:00"}])
    assert r.status_code == 422
    r = client.put(
        "/api/hours",
        headers=owner,
        json=[
            {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"},
            {"weekday": 0, "opens_at": "13:00", "closes_at": "18:00"},
        ],
    )
    assert r.status_code == 422
