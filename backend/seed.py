"""Fill the database with a demo salon so the UI has something to show.

    python seed.py
Login: demo@smartbooking.dev / demo-password
"""

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Appointment, AppointmentStatus, Business, Service, User, WorkingHours
from app.security import hash_password

DEMO_EMAIL = "demo@smartbooking.dev"
CUSTOMERS = [
    "Emma Johnson",
    "Liam Smith",
    "Olivia Brown",
    "Noah Davis",
    "Ava Wilson",
    "Lucas Martin",
    "Mia Garcia",
    "Ethan Moore",
    "Sofia Rossi",
    "Leo Clark",
    "Chloe Lewis",
    "Mason Hall",
]


def main() -> None:
    random.seed(42)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    old = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if old:
        db.query(Appointment).filter(Appointment.business_id == old.business.id).delete()
        db.delete(old)
        db.commit()

    user = User(email=DEMO_EMAIL, name="Demo Owner", hashed_password=hash_password("demo-password"))
    biz = Business(name="Bella Hair Studio", slug="bella-hair-studio")
    user.business = biz
    db.add(user)
    db.flush()

    services = [
        Service(business_id=biz.id, name=n, duration_minutes=d, price_cents=p)
        for n, d, p in [
            ("Haircut", 45, 3500),
            ("Color & Highlights", 120, 12000),
            ("Beard Trim", 30, 2000),
            ("Blow Dry", 30, 2800),
            ("Kids Cut", 30, 2200),
        ]
    ]
    db.add_all(services)
    db.add_all([WorkingHours(business_id=biz.id, weekday=d, opens_at=time(9), closes_at=time(18)) for d in range(5)])
    db.add(WorkingHours(business_id=biz.id, weekday=5, opens_at=time(9), closes_at=time(14)))
    db.flush()

    today = date.today()
    for offset in range(-24, 8):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:
            continue
        cursor = datetime.combine(day, time(9))
        closing = datetime.combine(day, time(14 if day.weekday() == 5 else 18))
        while True:
            svc = random.choices(services, weights=[6, 2, 4, 3, 2])[0]
            cursor += timedelta(minutes=random.choice([0, 0, 15, 30, 60]))
            end = cursor + timedelta(minutes=svc.duration_minutes)
            if end > closing:
                break
            if offset < 0:
                status = AppointmentStatus.CANCELLED if random.random() < 0.08 else AppointmentStatus.COMPLETED
            else:
                status = AppointmentStatus.BOOKED
            # the past and today look busy; upcoming days keep free slots for the booking page
            if random.random() < (0.85 if offset <= 0 else 0.45):
                name = random.choice(CUSTOMERS)
                db.add(
                    Appointment(
                        business_id=biz.id,
                        service_id=svc.id,
                        customer_name=name,
                        customer_email=name.lower().replace(" ", ".") + "@example.com",
                        customer_phone=f"+1 555 01{random.randint(10, 99)}",
                        start_at=cursor,
                        end_at=end,
                        status=status,
                        price_cents=svc.price_cents,
                    )
                )
            cursor = end
    db.commit()
    print(f"Seeded. Login: {DEMO_EMAIL} / demo-password  ·  booking page: /b/{biz.slug}")


if __name__ == "__main__":
    main()
