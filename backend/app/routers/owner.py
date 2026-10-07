"""Endpoints for the business owner (authenticated)."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Appointment, AppointmentStatus, Business, Service, WorkingHours
from app.schemas import (
    AppointmentOut,
    ServiceIn,
    ServiceOut,
    ServiceStat,
    StatsOut,
    StatusUpdate,
    WorkingHoursIn,
    WorkingHoursOut,
)
from app.security import get_current_business

router = APIRouter(prefix="/api", tags=["owner"])


def to_out(a: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=a.id,
        service_id=a.service_id,
        service_name=a.service.name,
        customer_name=a.customer_name,
        customer_email=a.customer_email,
        customer_phone=a.customer_phone,
        start_at=a.start_at,
        end_at=a.end_at,
        status=a.status,
        price_cents=a.price_cents,
    )


def own_service(db: Session, business: Business, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if service is None or service.business_id != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    return service


# --- services
@router.get("/services", response_model=list[ServiceOut])
def list_services(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return db.scalars(select(Service).where(Service.business_id == business.id).order_by(Service.name)).all()


@router.post("/services", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(data: ServiceIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    service = Service(business_id=business.id, **data.model_dump())
    db.add(service)
    db.commit()
    return service


@router.put("/services/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int, data: ServiceIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    service = own_service(db, business, service_id)
    for key, value in data.model_dump().items():
        setattr(service, key, value)
    db.commit()
    return service


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_service(
    service_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
) -> None:
    # Soft delete: past appointments keep pointing to the service.
    own_service(db, business, service_id).active = False
    db.commit()


# --- working hours
@router.get("/hours", response_model=list[WorkingHoursOut])
def get_hours(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return db.scalars(
        select(WorkingHours).where(WorkingHours.business_id == business.id).order_by(WorkingHours.weekday)
    ).all()


@router.put("/hours", response_model=list[WorkingHoursOut])
def set_hours(
    data: list[WorkingHoursIn], business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    """Replace the weekly schedule. Weekdays left out are closed."""
    if len({h.weekday for h in data}) != len(data):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Each weekday can appear only once")
    for row in db.scalars(select(WorkingHours).where(WorkingHours.business_id == business.id)):
        db.delete(row)
    db.flush()
    rows = [WorkingHours(business_id=business.id, **h.model_dump()) for h in data]
    db.add_all(rows)
    db.commit()
    return sorted(rows, key=lambda r: r.weekday)


# --- appointments
@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(
    start: date = Query(..., description="First day (inclusive)"),
    end: date = Query(..., description="Last day (inclusive)"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    if end < start or (end - start).days > 92:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid date range (max 92 days)")
    rows = db.scalars(
        select(Appointment)
        .where(
            Appointment.business_id == business.id,
            Appointment.start_at >= datetime.combine(start, datetime.min.time()),
            Appointment.start_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .order_by(Appointment.start_at)
    ).all()
    return [to_out(a) for a in rows]


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_status(
    appointment_id: int,
    data: StatusUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    appt = db.get(Appointment, appointment_id)
    if appt is None or appt.business_id != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    appt.status = data.status
    db.commit()
    return to_out(appt)


# --- dashboard
@router.get("/stats", response_model=StatsOut)
def stats(business: Business = Depends(get_current_business), db: Session = Depends(get_db)) -> StatsOut:
    now = datetime.now()
    today = datetime.combine(now.date(), datetime.min.time())
    month_start = today.replace(day=1)
    base = select(func.count(Appointment.id)).where(Appointment.business_id == business.id)
    active = Appointment.status != AppointmentStatus.CANCELLED

    today_count = db.scalar(
        base.where(active, Appointment.start_at >= today, Appointment.start_at < today + timedelta(days=1))
    )
    next_7 = db.scalar(
        base.where(active, Appointment.start_at >= now, Appointment.start_at < today + timedelta(days=8))
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Appointment.price_cents), 0)).where(
            Appointment.business_id == business.id,
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.start_at >= month_start,
        )
    )
    total_month = db.scalar(base.where(Appointment.start_at >= month_start)) or 0
    cancelled_month = (
        db.scalar(base.where(Appointment.status == AppointmentStatus.CANCELLED, Appointment.start_at >= month_start))
        or 0
    )
    top = db.execute(
        select(Service.name, func.count(Appointment.id), func.coalesce(func.sum(Appointment.price_cents), 0))
        .join(Service, Service.id == Appointment.service_id)
        .where(Appointment.business_id == business.id, active, Appointment.start_at >= month_start)
        .group_by(Service.name)
        .order_by(func.count(Appointment.id).desc())
        .limit(5)
    ).all()
    return StatsOut(
        today=today_count or 0,
        next_7_days=next_7 or 0,
        revenue_this_month_cents=revenue or 0,
        cancellation_rate=round(cancelled_month / total_month, 3) if total_month else 0.0,
        top_services=[ServiceStat(name=n, bookings=c, revenue_cents=r) for n, c, r in top],
    )
