from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_db
from app.models import Violation
from app.schemas import ScanResult, ViolationResponse
from app.services.scanner import run_deterministic_scan

router = APIRouter(tags=["violations"])


@router.get("/violations", response_model=list[ViolationResponse])
async def list_violations(
    rule_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ViolationResponse]:
    stmt = select(Violation)
    if rule_id:
        stmt = stmt.where(Violation.rule_id == rule_id)
    if status:
        stmt = stmt.where(Violation.status == status)
    stmt = stmt.order_by(Violation.detected_at.desc())

    result = await db.execute(stmt)
    violations = result.scalars().all()
    return [ViolationResponse.model_validate(v) for v in violations]


@router.get("/violations/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: int,
    db: AsyncSession = Depends(get_db),
) -> ViolationResponse:
    result = await db.execute(select(Violation).where(Violation.id == violation_id))
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return ViolationResponse.model_validate(violation)


@router.post("/scan", response_model=ScanResult)
async def trigger_scan() -> ScanResult:
    async with async_session_factory() as db:
        count = await run_deterministic_scan(db)
    return ScanResult(violations_found=count)
