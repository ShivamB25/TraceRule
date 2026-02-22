from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_db
from app.models import V3Rule, V3Violation
from app.schemas import (
    PaginatedViolationsResponse,
    V3RuleResponse,
    V3ScanResult,
    V3ViolationResponse,
    PolicyUploadResponse,
)

router = APIRouter(tags=["v3"])


async def _background_ingest_v3(
    file_bytes: bytes, filename: str, policy_id: int
) -> None:
    from app.services.ingestion import ingest_policy_v3

    async with async_session_factory() as db:
        await ingest_policy_v3(db, file_bytes, filename, policy_id)


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy_v3(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PolicyUploadResponse:
    file_bytes = await file.read()
    filename = file.filename or "unknown.pdf"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".md", ".markdown"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a .pdf or .md file.",
        )

    from app.models import Policy

    policy = Policy(filename=filename, markdown_text="", status="processing")
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    background_tasks.add_task(_background_ingest_v3, file_bytes, filename, policy.id)

    return PolicyUploadResponse(id=policy.id, filename=filename, status="processing")


@router.get("/rules", response_model=list[V3RuleResponse])
async def list_v3_rules(
    status: str | None = None,
    policy_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[V3RuleResponse]:
    stmt = select(V3Rule)
    if status:
        stmt = stmt.where(V3Rule.status == status)
    if policy_id:
        stmt = stmt.where(V3Rule.policy_id == policy_id)
    stmt = stmt.order_by(V3Rule.created_at.desc())

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [V3RuleResponse.model_validate(r) for r in rules]


@router.get("/rules/{rule_id}", response_model=V3RuleResponse)
async def get_v3_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> V3RuleResponse:
    result = await db.execute(select(V3Rule).where(V3Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="V3 rule not found")
    return V3RuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}/approve", response_model=V3RuleResponse)
async def approve_v3_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> V3RuleResponse:
    result = await db.execute(select(V3Rule).where(V3Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="V3 rule not found")
    rule.status = "approved"
    await db.commit()
    await db.refresh(rule)
    return V3RuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}/reject", response_model=V3RuleResponse)
async def reject_v3_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> V3RuleResponse:
    result = await db.execute(select(V3Rule).where(V3Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="V3 rule not found")
    rule.status = "rejected"
    await db.commit()
    await db.refresh(rule)
    return V3RuleResponse.model_validate(rule)


@router.get("/violations", response_model=PaginatedViolationsResponse)
async def list_v3_violations(
    v3_rule_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> PaginatedViolationsResponse:
    safe_limit = min(max(limit, 1), 500)
    safe_offset = max(offset, 0)

    stmt = select(V3Violation)
    count_stmt = select(func.count()).select_from(V3Violation)

    if v3_rule_id:
        stmt = stmt.where(V3Violation.v3_rule_id == v3_rule_id)
        count_stmt = count_stmt.where(V3Violation.v3_rule_id == v3_rule_id)
    if status:
        stmt = stmt.where(V3Violation.status == status)
        count_stmt = count_stmt.where(V3Violation.status == status)

    stmt = stmt.order_by(V3Violation.detected_at.desc())
    stmt = stmt.limit(safe_limit).offset(safe_offset)

    total_result = await db.execute(count_stmt)
    total_count = int(total_result.scalar_one())

    result = await db.execute(stmt)
    violations = result.scalars().all()
    return PaginatedViolationsResponse(
        items=[V3ViolationResponse.model_validate(v) for v in violations],
        total_count=total_count,
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get("/violations/{violation_id}", response_model=V3ViolationResponse)
async def get_v3_violation(
    violation_id: int,
    db: AsyncSession = Depends(get_db),
) -> V3ViolationResponse:
    result = await db.execute(select(V3Violation).where(V3Violation.id == violation_id))
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="V3 violation not found")
    return V3ViolationResponse.model_validate(violation)


@router.post("/scan", response_model=V3ScanResult)
async def trigger_v3_scan(
    db: AsyncSession = Depends(get_db),
) -> V3ScanResult:
    from app.services.scanner import run_v3_scan

    counts = await run_v3_scan(db, async_session_factory)
    return V3ScanResult(**counts)
