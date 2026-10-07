from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import AppointmentStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=2, max_length=120)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BusinessOut(ORM):
    id: int
    name: str
    slug: str


class MeOut(ORM):
    id: int
    name: str
    email: EmailStr
    business: BusinessOut


# --- services
class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    duration_minutes: int = Field(ge=5, le=8 * 60)
    price_cents: int = Field(ge=0, le=10_000_000)
    active: bool = True


class ServiceOut(ORM, ServiceIn):
    id: int


# --- working hours
class WorkingHoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: time
    closes_at: time

    @model_validator(mode="after")
    def check_range(self):
        if self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be after opens_at")
        return self


class WorkingHoursOut(ORM, WorkingHoursIn):
    pass


# --- appointments
class BookingIn(BaseModel):
    service_id: int
    start_at: datetime
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: EmailStr
    customer_phone: str = Field(default="", max_length=40)


class AppointmentOut(ORM):
    id: int
    service_id: int
    service_name: str
    customer_name: str
    customer_email: str
    customer_phone: str
    start_at: datetime
    end_at: datetime
    status: AppointmentStatus
    price_cents: int


class StatusUpdate(BaseModel):
    status: AppointmentStatus


# --- public
class PublicBusiness(BaseModel):
    name: str
    slug: str
    services: list[ServiceOut]
    hours: list[WorkingHoursOut]


class SlotsOut(BaseModel):
    date: date
    service_id: int
    slots: list[str]  # "HH:MM"


# --- dashboard
class ServiceStat(BaseModel):
    name: str
    bookings: int
    revenue_cents: int


class StatsOut(BaseModel):
    today: int
    next_7_days: int
    revenue_this_month_cents: int
    cancellation_rate: float
    top_services: list[ServiceStat]
