"""Public booking endpoints (no login): what customers use."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.availability import available_slots, overlaps
from app.config import get_settings
from app.database import get_db
from app.models import Appointment, AppointmentStatus, Business, Service, WorkingHours
from app.routers.owner import to_out
from app.schemas import AppointmentOut, BookingIn, PublicBusiness, SlotsOut

router = APIRouter(prefix="/api/public", tags=["public"])


def get_business(db: Session, slug: str) -> Business:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found")
    return business


def active_service(db: Session, business: Business, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if service is None or service.business_id != business.id or not service.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    return service


def busy_intervals(db: Session, business_id: int, day: date) -> list[tuple[datetime, datetime]]:
    start = datetime.combine(day, datetime.min.time())
    rows = db.execute(
        select(Appointment.start_at, Appointment.end_at).where(
            Appointment.business_id == business_id,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.start_at < start + timedelta(days=1),
            Appointment.end_at > start,
        )
    ).all()
    return [(r.start_at, r.end_at) for r in rows]


def slots_for(db: Session, business: Business, service: Service, day: date, now: datetime) -> list:
    hours = db.scalar(
        select(WorkingHours).where(WorkingHours.business_id == business.id, WorkingHours.weekday == day.weekday())
    )
    return available_slots(
        day,
        service.duration_minutes,
        hours.opens_at if hours else None,
        hours.closes_at if hours else None,
        busy_intervals(db, business.id, day),
        now,
        get_settings().slot_step_minutes,
    )


@router.get("/{slug}", response_model=PublicBusiness)
def business_page(slug: str, db: Session = Depends(get_db)) -> PublicBusiness:
    business = get_business(db, slug)
    return PublicBusiness(
        name=business.name,
        slug=business.slug,
        services=[s for s in business.services if s.active],
        hours=sorted(business.hours, key=lambda h: h.weekday),
    )


@router.get("/{slug}/slots", response_model=SlotsOut)
def slots(slug: str, service_id: int, day: date = Query(alias="date"), db: Session = Depends(get_db)) -> SlotsOut:
    business = get_business(db, slug)
    service = active_service(db, business, service_id)
    if day > date.today() + timedelta(days=90):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bookings open up to 90 days ahead")
    free = slots_for(db, business, service, day, datetime.now())
    return SlotsOut(date=day, service_id=service.id, slots=[t.strftime("%H:%M") for t in free])


@router.post("/{slug}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book(slug: str, data: BookingIn, db: Session = Depends(get_db)) -> AppointmentOut:
    business = get_business(db, slug)
    service = active_service(db, business, data.service_id)
    start = data.start_at.replace(tzinfo=None, second=0, microsecond=0)
    # Re-check availability on the server: the slot may have been taken since the page loaded.
    free = slots_for(db, business, service, start.date(), datetime.now())
    if start.time() not in free:
        raise HTTPException(status.HTTP_409_CONFLICT, "This time is no longer available")
    end = start + timedelta(minutes=service.duration_minutes)
    if any(overlaps(start, end, b, e) for b, e in busy_intervals(db, business.id, start.date())):
        raise HTTPException(status.HTTP_409_CONFLICT, "This time is no longer available")
    appt = Appointment(
        business_id=business.id,
        service_id=service.id,
        customer_name=data.customer_name.strip(),
        customer_email=data.customer_email.lower(),
        customer_phone=data.customer_phone.strip(),
        start_at=start,
        end_at=end,
        price_cents=service.price_cents,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return to_out(appt)
