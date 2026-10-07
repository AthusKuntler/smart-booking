# Smart Booking

Online appointment scheduling for service businesses (salons, barbers, clinics, studios).
Owners set up their services and opening hours. Customers get a public booking page that shows
only the times that are actually free, and no two bookings can overlap.

![Owner dashboard](docs/screenshots/dashboard.png)

| Public booking page | Mobile | Dark mode |
|---|---|---|
| ![Booking](docs/screenshots/booking.png) | ![Mobile](docs/screenshots/booking-mobile.png) | ![Dark](docs/screenshots/dashboard-dark.png) |

## Features

- **Owner accounts:** JWT authentication, one business per account, and an automatic public URL (`/b/your-business`).
- **Services:** name, duration and price. Hiding a service keeps the booking history intact.
- **Opening hours** for each weekday. Closed days never offer times.
- **Real availability engine:**
  - A slot is offered only if it fits inside opening hours, does not overlap an existing booking, and is in the future.
  - The server checks again when the booking is confirmed, so two customers can't take the same slot (HTTP 409).
- **Agenda:**
  - Day-by-day view with *done* and *cancel* actions.
  - KPIs: bookings today and for the next 7 days, revenue this month, cancellation rate.
  - Top services.
- **Price snapshot:** each booking stores the price at booking time, so later price changes don't rewrite history.
- **Responsive UI** with automatic light and dark themes.

## Tech stack

| Layer | Tools |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, bcrypt |
| Database | PostgreSQL (Docker) or SQLite (local dev / tests) |
| Web | React 19, TypeScript, Vite, React Router |
| Quality | pytest (18 tests), ruff, oxlint, GitHub Actions CI |
| Deploy | Docker Compose: Postgres + API + nginx serving the SPA and proxying `/api` |

## Run it

### With Docker (recommended)

```bash
docker compose up -d --build
docker compose exec api python seed.py   # optional demo data
```

Open http://localhost:8080. The demo login is `demo@smartbooking.dev` / `demo-password`, and the demo booking page is http://localhost:8080/b/bella-hair-studio.

### Local development

```bash
# API: http://localhost:8000 (interactive docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python seed.py
uvicorn app.main:app --reload

# Web: http://localhost:5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

### Tests and linters

```bash
cd backend && pytest -q && ruff check . && ruff format --check .
cd frontend && npx oxlint src && npm run build
```

## Configuration

These are environment variables, or put them in `backend/.env` (see `backend/.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./smart_booking.db` | e.g. `postgresql+psycopg://user:pass@host/db` |
| `JWT_SECRET` | dev-only value | **Set a long random value in production** |
| `JWT_EXPIRE_MINUTES` | `1440` | |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |

## API overview

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | none | Create the owner account and business |
| POST | `/api/auth/login` | none | OAuth2 password form, returns a JWT |
| GET | `/api/auth/me` | owner | Current user and business |
| GET/POST | `/api/services` | owner | List or create services |
| PUT/DELETE | `/api/services/{id}` | owner | Update or hide a service |
| GET/PUT | `/api/hours` | owner | Read or replace the weekly hours |
| GET | `/api/appointments?start=&end=` | owner | Agenda for a date range |
| PATCH | `/api/appointments/{id}` | owner | Mark as completed or cancelled |
| GET | `/api/stats` | owner | Dashboard KPIs |
| GET | `/api/public/{slug}` | none | Business info and active services |
| GET | `/api/public/{slug}/slots?service_id=&date=` | none | Free start times |
| POST | `/api/public/{slug}/appointments` | none | Book (409 if the slot was taken) |

Full interactive docs are at `/docs` (Swagger UI) while the API is running.

## Project structure

```
backend/
  app/
    availability.py   # pure slot-calculation logic (unit tested)
    models.py         # SQLAlchemy models
    routers/          # auth, owner, public endpoints
    security.py       # hashing, JWT, auth dependencies
  tests/              # API + availability tests
  seed.py             # demo data
frontend/
  src/pages/          # Dashboard, Services, Hours, Auth, public BookingPage
  nginx.conf          # production static server and API proxy
docker-compose.yml
```

## Roadmap ideas

- Email/SMS confirmations and reminders
- Multiple staff members per business
- Online deposits (Stripe)
- Time-zone support per business
