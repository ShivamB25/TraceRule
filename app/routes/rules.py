from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Rule
from app.schemas import RuleResponse, RuleStatusUpdate

router = APIRouter(tags=["rules"])


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    status: str | None = None,
    policy_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[RuleResponse]:
    stmt = select(Rule)
    if status:
        stmt = stmt.where(Rule.status == status)
    if policy_id:
        stmt = stmt.where(Rule.policy_id == policy_id)
    stmt = stmt.order_by(Rule.id)

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [RuleResponse.model_validate(r) for r in rules]


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return RuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}/status", response_model=RuleResponse)
async def update_rule_status(
    rule_id: int,
    body: RuleStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400, detail="Status must be 'approved' or 'rejected'"
        )

    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = body.status
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}/approve", response_model=RuleResponse)
async def approve_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = "approved"
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}/reject", response_model=RuleResponse)
async def reject_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = "rejected"
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)
