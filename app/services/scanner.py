import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.explainer import get_explainer_agent
from app.models import Violation

logger = logging.getLogger(__name__)


async def run_deterministic_scan(db: AsyncSession) -> int:
    result = await db.execute(
        text(
            "SELECT id, title, compiled_sql FROM rules "
            "WHERE status = 'approved' AND is_deterministic = true"
        )
    )
    violation_count = 0

    for rule in result.mappings():
        try:
            existing = await db.execute(
                text(
                    "SELECT record_pk FROM violations "
                    "WHERE rule_id = :rule_id AND status = 'open'"
                ),
                {"rule_id": rule["id"]},
            )
            known_pks: set[str] = {row[0] for row in existing}

            violators = await db.execute(text(rule["compiled_sql"]))
            for record in violators.mappings().all():
                pk = str(record.get("id", "unknown"))
                if pk in known_pks:
                    continue
                violation = Violation(
                    rule_id=rule["id"],
                    record_pk=pk,
                    violating_data=dict(record),
                )
                db.add(violation)
                known_pks.add(pk)
                violation_count += 1
        except Exception as e:
            logger.error("SQL execution failed for rule %d: %s", rule["id"], e)

    await db.commit()

    if violation_count:
        await _explain_new_violations(db)

    return violation_count


async def _explain_new_violations(db: AsyncSession) -> None:
    result = await db.execute(
        text(
            "SELECT v.id, v.violating_data, r.title, r.compiled_sql "
            "FROM violations v "
            "JOIN rules r ON v.rule_id = r.id "
            "WHERE v.ai_explanation IS NULL"
        )
    )

    for row in result.mappings():
        try:
            prompt = (
                f"Rule: {row['title']}\n"
                f"SQL: {row['compiled_sql']}\n"
                f"Violating data: {row['violating_data']}"
            )
            explanation_result = await get_explainer_agent().run(prompt)
            await db.execute(
                text(
                    "UPDATE violations SET ai_explanation = :explanation WHERE id = :id"
                ),
                {"explanation": explanation_result.output, "id": row["id"]},
            )
        except Exception as e:
            logger.error("Explanation failed for violation %d: %s", row["id"], e)

    await db.commit()
