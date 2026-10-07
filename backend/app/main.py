from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, owner, public


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Small project: tables are created on startup. A larger one would use Alembic migrations.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Smart Booking API",
    description="Online booking for small service businesses.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(owner.router)
app.include_router(public.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
