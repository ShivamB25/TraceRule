import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory, engine
from app.models import Base
from app.services.scanner import run_deterministic_scan

logger = logging.getLogger(__name__)


async def scheduled_scan() -> None:
    async with async_session_factory() as db:
        count = await run_deterministic_scan(db)
        if count:
            logger.info("Scan complete: %d new violations detected", count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scheduled_scan,
        IntervalTrigger(minutes=settings.scan_interval_minutes),
        id="compliance-scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — scanning every %d minutes", settings.scan_interval_minutes
    )

    yield

    scheduler.shutdown(wait=False)
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(title="TraceRule", version="3.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import policies, rules, violations

app.include_router(policies.router, prefix="/api/v1")
app.include_router(rules.router, prefix="/api/v1")
app.include_router(violations.router, prefix="/api/v1")

from app.api import router as v3_router

app.include_router(v3_router.router, prefix="/api/v3")
